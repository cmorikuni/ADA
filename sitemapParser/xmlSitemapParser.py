import os
import sys
import json
import re
import argparse
from BeautifulSoup import BeautifulSoup as bs


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="XML Sitemap Parser")
    parser.add_argument('--sitemap', help='file path to the sitemap')
    args = parser.parse_args()

    if not args.sitemap:
        sys.exit("ERROR: a sitemap (--sitemap) is not defined")

    soup = bs(open(args.sitemap))

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
        if m and m.group(len(m.groups())) not in [".html", ".htm", ".asp", ".aspx"]:
            print "Skipping: " + url.text
            continue

        url_struct = {"url": url.text}
        ret_arr.append(url_struct)

    outfile = os.path.basename(args.sitemap).split('.')
    outfile = outfile[0] + ".json"
    text = json.dumps(ret_arr, indent=2)
    with open(outfile, "w") as f:
        f.write(text)
    print "Writing output to: " + outfile