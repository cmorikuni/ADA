import os
import errno
import sys
import json
import re
import argparse
from BeautifulSoup import BeautifulSoup as bs

class PySitemapParser(object):
    infile = ""
    outfile = ""

    def __init__(self, inputFile, outputFile):
        if not os.path.isfile(inputFile):
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), inputFile)
        if not os.path.isfile(outputFile):
            raise FileNotFoundError(
                errono.ENOENT, os.strerror(errno.ENOENT), outputFile)
        self.infile = inputFile
        self.outfile = outputFile

    def parse(self):
        soup = bs(open(self.infile))
        # get loc
        # ignore .* extensions unless its html or htm
        # add url to dictionary
        # in structured form:
        # [
        #   {
        #     "url": "http://www.revacomm.com/../services/information-technology/"
        #   },
        #   {
        #     "url": "http://www.revacomm.com/industries/corporate/"
        #   },
        #   {
        #     "url": "http://www.revacomm.com/contact"
        #   }
        # ]
        ret_arr = []
        urls = soup.findAll('loc')
        for url in urls:
            # Skip urls with extensions unless noted
            m = re.search(r'.*(\.\w*)$', url.text)
            if m and m.group(len(m.groups())) not in [".html", ".htm", ".asp", ".aspx", ".jsp"]:
                print "Skipping: " + url.text.encode("utf-8")
                continue

            url_struct = {"url": url.text}
            ret_arr.append(url_struct)

        text = json.dumps(ret_arr, indent=2)
        with open(self.outfile, "w") as f:
            f.write(text)
        print "Writing output to: " + self.outfile