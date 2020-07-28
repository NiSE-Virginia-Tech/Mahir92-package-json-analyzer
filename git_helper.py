from datetime import datetime
from datetime import timedelta
import constants
import requests
from bs4 import BeautifulSoup
import json


class GitHelper:

    def __init__(self, dependency_type):
        self.api_url = api_url = "https://api.github.com/search/repositories?q=%20language:javascript+created:{start_date}..{end_date}&sort=stars&order=desc&type=repository&page={page_no}&order={order}"
        self.ok_to_process_repos = []
        self.date_format = "%Y-%m-%" + "d"
        self.dependency_type = dependency_type
        self.no_of_collected_repos = 0

    def get_ok_to_process_repos(self):
        self.crawlProject()
        return self.ok_to_process_repos

    def crawlProject(self):
        end_date = datetime.today()

        while(True):
            start_date = end_date + timedelta(days=-constants.DATE_INTERVAL)

            start_date_str = start_date.strftime(self.date_format)
            end_date_str = end_date.strftime(self.date_format)

            self.crawlProjectsInRange(start_date_str, end_date_str)

            if(self.no_of_collected_repos >= constants.LIMIT_OF_COLLECTED_REPOS):
                break

            if(start_date_str[:4:] == constants.YEAR_LIMIT):
                break

            end_date = start_date + timedelta(days=-1)

    def crawlProjectsInRange(self, start_date_str, end_date_str):

        for page in range(1, 34):

            if(self.no_of_collected_repos >= constants.LIMIT_OF_COLLECTED_REPOS):
                break

            api_url = self.api_url.format(
                start_date=start_date_str, end_date=end_date_str, page_no=page, order=constants.ORDER)

            response = requests.get(api_url)

            repos = response.json()['items']

            for repo in repos:
                user = repo['owner']['login']
                repo_name = repo['name']
                repo_url = 'https://github.com/%s/%s' % (user, repo_name)

                if(self.ok_to_process(repo_url)):
                    self.ok_to_process_repos.append(repo_url)
                    self.no_of_collected_repos += 1

                    if(self.no_of_collected_repos >= constants.LIMIT_OF_COLLECTED_REPOS):
                        break

    def ok_to_process(self, repo_url):
        repo_link = repo_url.replace("github.com", "raw.githubusercontent.com")
        config_file = repo_link + "/master/package.json"

        page = requests.get(config_file)

        if(page.status_code == constants.ERROR_CODE_NOT_FOUND):
            return False

        try:

            soup = BeautifulSoup(page.content, 'html.parser')
            package_json = json.loads(soup.text)

            # we are not counting repos with no dependencies
            # package_json acts like a dictionary
            if self.dependency_type in package_json:
                no_of_dependencies = len(package_json[self.dependency_type])
            else:
                no_of_dependencies = 0

            # only processing repos with build scripts
            has_proper_build_scripts = True
            if constants.TAG_SCRIPTS in package_json:
                scripts = package_json[constants.TAG_SCRIPTS]
                if(len(scripts) == 0):
                    has_proper_build_scripts = False
                else:
                    # ignoring if any build script has "exit 1" in it
                    # script is a dictionary
                    for script in scripts:
                        if "exit 1" in scripts[script]:
                            has_proper_build_scripts = False
                            break

            return (no_of_dependencies > 0) & has_proper_build_scripts
        except:
            return False