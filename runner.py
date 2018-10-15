from pa11y.pa11y import Pa11yPy
from datetime import datetime
from junit_xml import TestSuite, TestCase
import os
import sys
import re
import json
import argparse
import pysitemap
from sitemapParser import PySitemapParser


outfile = "sitemap.txt"

"""
items = [{"url": "www.address.com"}, {}]
dictionary of URL objects. Additional keys are:

actions (array)
    click element <selector>
    set field <selector> to <value>
    check field <selector>
    uncheck field <selector>
    screen capture <file-path>
    wait for fragment to be <fragment> (including the preceding #)
    wait for fragment to not be <fragment> (including the preceding #)
    wait for path to be <path> (including the preceding /)
    wait for path to not be <path> (including the preceding /)
    wait for url to be <url>
    wait for url to not be <url>
    wait for element <selector> to be added
    wait for element <selector> to be removed
    wait for element <selector> to be visible
    wait for element <selector> to be hidden
    wait for element <selector> to emit <event-type>
    navigate to <url>
browser (string)
chromeLaunchConfig (string)
headers (object)
hideElements (string)
ignore (array)
includeNotices (boolean)
includeWarnings (boolean)
level (string)
log (object)
method (string)
postData (string or object)
reporter (string)
rootElement (element)
rules (array)
screenCapture (string) - enabled for all pages in the pa11y interface
standard (string)
threshold (number)
timeout (number)
userAgent (string)
viewport (object)
wait (number)
"""


def parseUrl(url, doExit=True):
    # regex for URL matching
    regex = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' # domain...
        r'localhost|' # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|' # ...or ipv4
        r'\[?[A-F0-9]*:[A-F0-9:]+\]?)' # ...or ipv6
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    if regex.match(url) is None:
        print "ERROR: invalid URL format. http://...: " + url
        if doExit:
            sys.exit(-1)
    else:
        return url
    return None


def url_basename(url):
    restr = url.split("//")
    basename = restr[len(restr)-1].replace(".", "_").replace("/", "_")
    return basename


def crawlWebsite(url, outputFile):
    # outputs a list of webpages
    logfile = 'errlog.log'  # path to logfile
    oformat = 'txt'  # output format
    crawl = pysitemap.Crawler(url=url, outputfile=outputFile, logfile=logfile, oformat=oformat)
    crawl.crawl(pool_size=10)  # 10 parsing processes


def buildPageDict(inputFile, outputFile):
    items = []
    pageSet = set()
    with open(inputFile, 'r') as f:
        for page in f:
            page = page.rstrip()
            if not page in pageSet: # and parseUrl(page, False):
                items.append({"url": page})
                pageSet.add(page)

        text = json.dumps(items, indent=2)
        with open(outputFile, "w") as f:
            f.write(text)
        print "JSON configuration file found at: " + outputFile
    return items


def writeJunit(res_path, results):
    tcs = []
    for result in results["summary"]:
        res_out = str(result["results"]["notice"] + result["results"]["warning"]) + " warnings/notices were found."
        res_err = result["results"]["error"]
        tc = TestCase(result["url"], result["url"], result["time"], res_out, '')
        if res_err > 0:
            tc.add_error_info(str(res_err) + " errors were found.")
        tcs.append(tc)

    ts = [TestSuite('ADA Test Suite', tcs)]
    path = os.path.join(res_path, "junitResult.xml")
    with open(path, 'w') as f:
        TestSuite.to_file(f, ts)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="ADA Compliance Tester")
    parser.add_argument('--path', help='base path for results storage')
    parser.add_argument('--action', choices=['crawl', 'sitemap', 'json'], default='crawl', help='choose action to perform')
    parser.add_argument('--url', help="url for the crawler to scan")
    parser.add_argument('--sitemap', help="sitemap to parse")
    parser.add_argument('--jsonfile', help="json file to scan")
    parser.add_argument('--standard', choices=['Section508', 'WCAG2A', 'WCAG2AA', 'WCAG2AAA'], default='WCAG2AA', help='choose an ADA standard')
    args = parser.parse_args()

    if not args.path:
        sys.exit("ERROR: a base path (--path) is not defined")
    if args.action == 'crawl' and not args.url:
        sys.exit("ERROR: crawl choosen and --url is not defined")
    if args.action == 'sitemap' and not args.sitemap:
        sys.exit("ERROR: sitemap choose and --sitemap is not defined")
    if args.action == 'json' and not args.jsonfile:
        sys.exit("ERROR: json choosen and --jsonfile is not defined")

    if args.action == 'crawl':
        url = parseUrl(args.url)  # url from to crawl
        print "Executing a crawl on: " + url
        start = datetime.now()
        crawlWebsite(url, outfile)
        end = datetime.now()
        delta = end - start
        print "Crawler time: " + str(delta) + "\n"

        # Output URL configuration file
        url_base = url_basename(url)
        items = buildPageDict(outfile, url_base + ".json")
    elif args.action == 'sitemap':
        PySitemapParser.PySitemapParser(args.sitemap, outfile).parse()

        # Output URL configuration file
        print os.path.splitext(args.sitemap)[0]
        items = buildPageDict(outfile, os.path.splitext(args.sitemap)[0] + ".json")
    else:  # load from JSON file
        with open(args.jsonfile) as json_data:
            items = json.load(json_data)

    # Run ADA scan
    print "Standard: " + args.standard
    print "The site has " + str(len(items)) + " pages"
    if args.action == 'json':
        resp = 'Y'
    else:
        resp = raw_input("\nRun ADA scan (Y or N): ")
    if resp == 'Y':
        start = datetime.now()
        # ensure that results are stored one level deeper
        res_path = os.path.join(args.path, "results")
        pa11y = Pa11yPy(res_path, args.standard)
        itemCnt = 0
        for item in items:
            itemCnt += 1
            itemStatusText = "%d of %d" % (itemCnt, len(items))
            res = pa11y.process_item(item)
            if res.get("results"):
                print "Scanned (" + itemStatusText + "): " + json.dumps(res["results"]) + " " + res["url"]
            else:
                print "ERROR: no results were generated from: " + item["url"]
        end = datetime.now()
        delta = end - start
        print "Processing time: " + str(delta)

        agg_res = pa11y.get_aggregate_results()
        pa11y.write_results_summary()
        writeJunit(args.path, agg_res)

        #print "\nSummary:"
        #print json.dumps(agg_res, indent=2)
    else:
        sys.exit("ADA scan exited without running")

    if agg_res["error"] > 0:
        sys.exit("FAILED: %d errors detected" % agg_res["error"])