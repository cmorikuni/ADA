import os
import sys
import json
import re
import fnmatch
import subprocess as sp
import tempfile
#import hashlib
#import itertools
import logging
import cgi
#from lxml import html
from datetime import datetime
from BeautifulSoup import BeautifulSoup as bs
from jinja2 import Environment, PackageLoader, FileSystemLoader
from path import Path

# pa11y-reporter-html musl be in the same node directory that's being used

DEVNULL = open(os.devnull, 'wb')
RES_PATH = "results"
INDEX_TEMPLATE = 'index.html'
ASSESS_TEMPLATE = 'report.html'


def resource_path(relative_path):
    """ Get absolute path to resource, works for both in IDE and for PyInstaller """
    # PyInstaller creates a temp folder and stores path in sys._MEIPASS
    # In IDE, the path is os.path.join(base_path, relative_path)
    # Search in Dev path first, then MEIPASS
    base_path = os.path.abspath(".")
    dev_file_path = os.path.join(base_path, relative_path)
    if os.path.exists(dev_file_path):
        return dev_file_path
    else:
        base_path = sys._MEIPASS
        dev_file_path = os.path.join(base_path, relative_path)
        if not os.path.exists(dev_file_path):
            msg = "\nError finding resource in either {}".format(dev_file_path)
            logging.error(msg)
            return None
        return dev_file_path


class Pa11yPy(object):
    """
    Runs the Pa11y CLI
    """
    result_path = RES_PATH
    pa11y_path = "pa11y"
    cli_flags = {
        "reporter": "json",
    }

    agg_result = {
        "error": 0,
        "warning": 0,
        "notice": 0,
        "summary": [],
        "guidelines": {}
    }

    def __init__(self, path, standard):
        self.reset_aggregate_results()
        self.result_path = path
        self.cli_flags["standard"] = standard

        """
        Check for proper installs and versions
        """
        try:
            pa11y_ver = sp.check_output(
                [self.pa11y_path, "--version"],
                shell=True, stderr=DEVNULL,
            )
        except sp.CalledProcessError:
            # No file or directory exists
            msg = (
                "pa11y is not globally installed at {path}. "
                "Run `npm install -g pa11y` to install it."
            ).format(path=self.pa11y_path)
            raise OSError(msg)

        # Need to check for PhantomJS, since only 5.0+ supports headless chromedriver
        if self.vercmp(pa11y_ver, "5.0") < 0:
            try:
                sp.check_call(
                    ["phantomjs", "--version"],
                    shell=True, stdout=DEVNULL, stderr=DEVNULL,
                )
            except OSError:
                # No such file or directory
                msg = (
                    "phantomjs is not installed, and pa11y cannot run without it. "
                    "Install phantomjs through your system package manager."
                )
                raise OSError(msg)

        # Setup result path name
        self.result_path = self.result_path + "_" + datetime.now().strftime('%Y-%m-%d_%H-%M-%S')


    def vercmp(self, ver1, ver2):
        def normalize(v):
            return [int(x) for x in re.sub(r'(-beta)','', v).split(".")]
        return cmp(normalize(ver1), normalize(ver2))


    def process_item(self, item):
        start = datetime.now()

        basename = self.pa11y_results_basename(item)
        config_file = self.write_pa11y_config(item, basename)
        args = [
            self.pa11y_path,
            item["url"],
            '--config={file}'.format(file=config_file.name),
        ]
        for flag, value in self.cli_flags.items():
            args.append("--{flag}={value}".format(flag=flag, value=value))

        retries_remaining = 3
        while retries_remaining:
            logline = " ".join(args)
            if retries_remaining != 3:
                logline += "  # (retry {num})".format(num=3-retries_remaining)
                logging.error(logline)

            proc = sp.Popen(
                args, shell=True,
                stdout=sp.PIPE, stderr=sp.PIPE,
            )
            stdout, stderr = proc.communicate()
            if proc.returncode in (0, 2):
                # `pa11y` ran successfully!
                # Return code 0 means no a11y errors.
                # Return code 2 means `pa11y` identified a11y errors.
                # Either way, we're done, so break out of the `while` loop
                break
            else:
                # `pa11y` did _not_ run successfully!
                # We sometimes get the error "Truffler timed out":
                # truffler is what accesses the web page for `pa11y1`.
                # https://www.npmjs.com/package/truffler
                # If this is the error, we can resolve it just by trying again,
                # so decrement the retries_remaining and start over.
                retries_remaining -= 1

        if retries_remaining == 0:
            logging.info(
                "Couldn't get pa11y results for {url}. Error:\n{err}".format(
                    url=item['url'],
                    err=stderr,
                )
            )
        else:
            item['accessed_at'] = datetime.utcnow().strftime('%B %d %Y - %H:%M:%S')
            pa11y_results = self.load_pa11y_results(stdout, item)
            os.remove(config_file.name)
            self.pa11y_counts(pa11y_results, item)
            self.write_pa11y_dual_results(item, pa11y_results, basename)

        end = datetime.now()
        delta = end - start
        item['time'] = delta.total_seconds()
        return item


    def load_pa11y_results(self, stdout, item):
        url = item["url"]
        if not stdout:
            return []

        results = stdout
        results = json.loads(results.decode('utf8'))

        return results


    def write_pa11y_config(self, item, basename):
        filename = basename + '.png'
        filepath = os.path.join(self.result_path, filename)
        config = {
            "headers": item.get("request_headers", ""),
        }
        # CM: turned off screen capture - need to create this as an arg option
        #config = {
        #    "headers": item.get("request_headers", ""),
        #    "screenCapture": filepath,
        #}
        config_file = tempfile.NamedTemporaryFile(
            mode="w",
            prefix="pa11y-config-",
            suffix=".json",
            delete=False
        )
        json.dump(config, config_file)
        config_file.close()
        item["img"] = filename
        return config_file


    def pa11y_counts(self, results, item):
        # Init counts
        num_error = 0
        num_warning = 0
        num_notice = 0

        if not results:
            return

        guideCntDict = {}
        for result in results:
            # level counts
            if result['type'] == 'error':
                num_error += 1
            elif result['type'] == 'warning':
                num_warning += 1
            elif result['type'] == 'notice':
                num_notice += 1

            # guidelines counts
            code = result.get("code")
            if code:
                if code in guideCntDict:
                    guideCntDict[code]["count"] += 1
                else:
                    guideCntDict[code] = {"message": result.get("message"), "count": 1}

                # Aggregate guidelines
                if code in self.agg_result["guidelines"]:
                    self.agg_result["guidelines"][code]["count"] += 1
                else:
                    self.agg_result["guidelines"][code] = {"message": result.get("message"), "count": 1}

        item["results"] = {"error": num_error, "warning": num_warning, "notice": num_notice}
        item["guidelines"] = guideCntDict

        # Aggregate results for summarization
        self.agg_result["error"] += num_error
        self.agg_result["warning"] += num_warning
        self.agg_result["notice"] += num_notice
        self.agg_result["summary"].append(item)


    def pa11y_results_basename(self, item):
        restr = item["url"].split("//")
        basename = restr[len(restr)-1].replace(".", "_").replace("/", "_")
        return basename


    def unicodeToHtmlEntities(self, text):
        text = cgi.escape(text).encode('ascii', 'xmlcharrefreplace')
        return text


    # CM: change to truncated and hashed filenames for really long filenames
    # CM: ex \\results_2018-10-08_17-08-24\\www_asbhawaii_com_node_57_mid_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_checking_biz-simple-checking.json
    def write_pa11y_dual_results(self, item, pa11y_results, basename):
        data = dict(item)
        data['pa11y'] = pa11y_results

        sub_path = os.path.join("pa11y", "templates")
        temp_path = resource_path(sub_path)

        loader = FileSystemLoader(searchpath=temp_path)
        env = Environment(loader=loader)

        if not os.path.exists(self.result_path):
            os.makedirs(self.result_path)

        json_file = basename + ".json"
        json_path = os.path.join(self.result_path, json_file)
        html_file = basename + ".html"
        html_path = os.path.join(self.result_path, html_file)

        # encode html entities
        for res in pa11y_results:
            res["message"] = self.unicodeToHtmlEntities(res["message"])
            res["selector"] = self.unicodeToHtmlEntities(res["selector"])
            res["context"] = self.unicodeToHtmlEntities(res["context"])

        # Write html
        assess_path = Path(html_path).expand()
        self.render_template(env, assess_path, ASSESS_TEMPLATE, {
            "pageUrl": item["url"],
            "date": item["accessed_at"],
            "errorCount": item["results"]["error"],
            "warningCount": item["results"]["warning"],
            "noticeCount": item["results"]["notice"],
            "issues": pa11y_results,
            "guidelines": json.dumps(item["guidelines"])
        })
        item["html_report"] = html_file

        # Write json
        text = data["pa11y"]
        text = json.dumps(data, cls=DateTimeEncoder, indent=2)
        with open(json_path, "w") as f:
            f.write(text)
            item["json_report"] = json_file


    def get_aggregate_results(self):
        return self.agg_result


    def reset_aggregate_results(self):
        # Reset aggregate results
        self.agg_result = dict.fromkeys(self.agg_result, 0)
        self.agg_result["summary"] = []
        self.agg_result["guidelines"] = {}


    def render_template(self, env, html_path, template_filename, context):
        """
        Render a template file into the given output location.
        """
        template = env.get_template(template_filename)
        rendered_html = template.render(**context)  # pylint: disable=no-member
        html_path.write_text(rendered_html, encoding='utf-8')


    def write_results_summary(self):
        sub_path = os.path.join("pa11y", "templates")
        temp_path = resource_path(sub_path)

        loader = FileSystemLoader(searchpath=temp_path)
        env = Environment(loader=loader)

        index_path = Path(os.path.join(self.result_path, "summary.html")).expand()
        self.render_template(env, index_path, INDEX_TEMPLATE, {
            "pages": self.agg_result["summary"],
            "num_error": self.agg_result["error"],
            "num_warning": self.agg_result["warning"],
            "num_notice": self.agg_result["notice"],
            "guidelines": json.dumps(self.agg_result["guidelines"])
        })


class DateTimeEncoder(json.JSONEncoder):
    "A JSON encoder that can handle datetimes"
    def default(self, o):  # pylint: disable=method-hidden
        if isinstance(o, datetime):
            return o.isoformat()
        return JSONEncoder.default(self, o)