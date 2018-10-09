# 508_Testing

# WARNING:
This tool can aid in ADA testing but it will not find every issue. This tools should complement your manual ADA testing workflow.

# Pa11y
Open source ADA compliance tool. Out of the box it allows for different running modes and reporting formats. It can be difficult to setup and configure for a large site thus the creation of PyPa11y wrapper.

## Windows 10 Install

node -v
* version must be > 8

npm install -g pa11y@beta
* using pa11y 5 to take advantage of headless chrome, only supported in beta

npm install -g pa11y-reporter-html
* pa11y comes default with json reporting. We want the option to use both json and html reports.

pa11y looking in C:\Program File\nodejs\node_modules\pa11y
* may need to copy from C:\Users\username\AppData\Roaming\npm\node_modules\pa11y

to execute on cmd: pa11y http://www.google.com

## Packaging pa11y
Can package pa11y with \node_modules\pa11y> pgk ./package.json, but pa11y needs puppeteer and chromium. Puppeteer and chromium doesn't get included in the exe and shouldn't be because of how often chromium gets updated. Users will have to install node.js and the proper modules or we'll need to find another way to package pa11y but easily allow chromium to be updated.

## Resources
* http://pa11y.org/
* https://github.com/pa11y/pa11y-ci
* http://jpedroribeiro.com/2018/01/accessibility-tests-with-pa11y-node/
    * sample code needs timeout handling of promises
* https://github.com/pa11y/pa11y#actions
* https://pypi.org/project/junit-xml/

# PyPa11y
PyPa11y is a wrapper that allows pa11y to run through python. It utilizes the command line execution of pa11y. It also aggregates the results for all urls run through an instance of the class. The default standard used is WCAG2AA.

The runner.py portion is an interface to PyPa11y. This interface supports crawling a site or json input. If using the crawler the user will be prompted to run the scan. Modifying the json input allows users to setup custom options per page and to setup actions to get through authenitcation walls.

The JSON schema is an array of dictionaries:
    ```
    [
      {
        "url": "http://www.revacomm.com/../services/information-technology/"
      },
      {
        "url": "http://www.revacomm.com/industries/corporate/"
      },
    ]
    ```
The supported keys can be found here: https://github.com/pa11y/pa11y#configuration

## Additional Modules to Install
pip install BeautifulSoup
pip install Jinja2
pip install path.py
pip install junit-xml

## Notes
* Wrapper uses pa11y cli commands doesn't allow for multiple output types in a single run (either html or json)
* We can rewrite the reporter to support multiple types in a single run (gotta figure out how)
* tried using a python to js bridge, but couldn't find any modules that works well enough to utilize the js pa11y API
* Will overwrite results if run on the same URL multiple times
* https://www.digitalocean.com/community/tutorials/how-to-package-and-distribute-python-applications

## TODO
* pa11y actions for login or form filling hasn't been tested
* Still need to find a better site crawler
* Create a Jenkins plugin out of all of this
* Logging
* Add other options for screen capture and standards setting
* Aggregate on guidelines per page and across site

## Packaging PyPa11y
* pip install pyinstaller
* pyi-makespec entry_point.py -n app_name --onefile
    - entry_point.py is where __main__ is located
    - app_name is the name of your executable
    - this command creates app_name.spec
* modify app_name.spec to add resources
    - array of tuples
    - first string is the path of the file or files
    - name of the folder to contain the files at run-time
    - datas=[('.\\pa11y\\templates' ,'.\\pa11y\\templates')] - if you keep the paths the same it makes it easier to find the files in pa11y.py:resource_path(relative_path)
* pyinstaller app_name.spec --onefile

# XML Sitemap Parser
Generates the PyPa11y json from an xml sitemap
* get <loc> tag
* ignore .* extensions unless its html, htm, asp, or aspx
* add url to dictionary
    * in structured form:
    ```
    [
      {
        "url": "http://www.revacomm.com/../services/information-technology/"
      },
      {
        "url": "http://www.revacomm.com/industries/corporate/"
      },
    ]
    ```

# Jenkins Job Setup
* BUILD: Execute Windows Batch Command
    - C:\PyAdaScanner\PyAdaScanner --path "%WORKSPACE%" --action json --jsonfile "%WORKSPACE%\www_short_com.json"
* POST-BUILD: Archive The Artifacts
    - resuts_*/*.*
* POST-BUILD: Publish JUnit Test Result Report
    - junitResult.xml
    - Check "Do not fail the build on empty test results"

# Estimation Sections
architecture (24)
- auto scaling
- partitioning jobs

configuration/setup (40)
- config scripts
- containers

user interface (24)

tools interface (80)

results aggregation (80)

deployment (40)

testing/documentation (40)