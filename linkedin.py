"""
Provides linkedin api-related code
"""
import csv
import math
import random
from time import sleep

from client import Client


def default_evade():
    """
    A catch-all method to try and evade suspension from Linkedin.
    Currenly, just delays the request by a random (bounded) time
    """
    sleep(random.randint(2, 5))  # sleep a random duration to try and evade suspention


class Linkedin(object):
    """
    Class for accessing Linkedin API.
    """

    def __init__(
            self,
            username,
            password,
            *,
            authenticate=True,
            refresh_cookies=False,
            debug=False,
            proxies={},
            cookies=None,
    ):
        self.client = Client(
            refresh_cookies=refresh_cookies, debug=debug, proxies=proxies
        )

        if authenticate:
            if cookies:
                # If the cookies are expired, the API won't work anymore since
                # `username` and `password` are not used at all in this case.
                self.client._set_session_cookies(cookies)
            else:
                self.client.authenticate(username, password)

    def _fetch(self, uri, evade=default_evade, base_request=False, **kwargs):
        """
        GET request to Linkedin API
        """
        evade()

        url = f"{self.client.API_BASE_URL if not base_request else self.client.LINKEDIN_BASE_URL}{uri}"
        return self.client.session.get(url, **kwargs)

    def _post(self, uri, evade=default_evade, base_request=False, **kwargs):
        """
        POST request to Linkedin API
        """
        evade()

        url = f"{self.client.API_BASE_URL if not base_request else self.client.LINKEDIN_BASE_URL}{uri}"
        return self.client.session.post(url, **kwargs)

    def get_profile_skills(self, public_id=None, urn_id=None):
        """
        Return the skills of a profile.

        [public_id] - public identifier i.e. tom-quirk-1928345
        [urn_id] - id provided by the related URN
        """
        params = {"count": 100, "start": 0}
        res = self._fetch(
            f"/identity/profiles/{public_id or urn_id}/skills", params=params
        )
        data = res.json()

        skills = data.get("elements", [])
        for item in skills:
            del item["entityUrn"]

        return skills

    def scrape_student_info(self):
        """
        to-do
        """
        csv_field_names = ['student_name',
                           'linkedin_url',
                           'remarks',
                           'education -> List(school_name, degree_name, field_of_study, decsription)',
                           'certifications -> List(certifying_authority, certification_name)',
                           'experience -> List(designation, company_name, tenure, description)',
                           'skills -> List of all skills & tools']
        self.write_to_csv_file(csv_field_names, mode='w')
        profile_not_found = []
        records_processed = 0
        with open('input_file.csv') as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            for row in csv_reader:
                student_linkedin_profile_url = row[1]
                student_profile_id = student_linkedin_profile_url.split('/')[4] if student_linkedin_profile_url else \
                    None
                if student_profile_id:
                    profile = self.get_profile(public_id=student_profile_id)
                    if not profile:
                        profile_not_found.append(student_linkedin_profile_url)
                        self.write_to_csv_file([row[0],
                                                row[1],
                                                'Invalid profile url',
                                                '',
                                                '',
                                                '',
                                                '']
                                               )
                    else:
                        self.write_to_csv_file([row[0],
                                                row[1],
                                                'Successful',
                                                profile.get('education'),
                                                profile.get('certifications'),
                                                profile.get('experience'),
                                                profile.get('skills')]
                                               )
                else:
                    self.write_to_csv_file([row[0],
                                            row[1],
                                            'Student has not updated profile url',
                                            '',
                                            '',
                                            '',
                                            ''])
                records_processed += 1
                print('No of records processed: {}'.format(records_processed))
                sleep(1)
        print('Execution completed successfully. Hurray!')

    def write_to_csv_file(self, row_to_write, mode='a'):
        """
        :param mode: append
        :param row_to_write: row data to be written into csv
        """
        with open('student_profile_data.csv', mode=mode) as student_profile_data_file:
            csv_writer = csv.writer(student_profile_data_file)
            csv_writer.writerow(row_to_write)

    def get_profile(self, public_id=None, urn_id=None):
        """
        :param public_id: linkedin profile id
        :param urn_id:
        """
        res = self._fetch(f"/identity/dash/profiles?q=memberIdentity&memberIdentity="
                          f"{public_id or urn_id}&decorationId=com.linkedin"
                          f".voyager.dash.deco.identity.profile.FullProfileWithEntities-47")

        data = res.json()
        if data and "status" in data and data["status"] != 200:
            print("request failed: {}".format(data["message"]))
            return {}

        profile = {'education': [],
                   'certifications': [],
                   'experience': [],
                   'skills': []}

        education_list = data['elements'][0]['profileEducations']['elements']
        certifications_list = data['elements'][0]['profileCertifications']['elements']
        experience_list = data['elements'][0]['profilePositionGroups']['elements']
        skills = self.get_profile_skills(public_id=public_id)

        for ed in education_list:
            profile['education'].append([ed.get('schoolName').strip() if ed.get('schoolName') else None,
                                         ed.get('degreeName').strip() if ed.get('degreeName') else None,
                                         ed.get('fieldOfStudy').strip() if ed.get('fieldOfStudy') else None,
                                         ed.get('description').strip() if ed.get('description') else None,
                                         ])
        for cert in certifications_list:
            profile['certifications'].append([cert.get('authority').strip() if cert.get('authority') else None,
                                              cert.get('name').strip()] if cert.get('name') else None)
        for exp in experience_list:
            for ex in exp.get('profilePositionInPositionGroup').get('elements'):
                start = '{},{}'.format(ex.get('dateRange').get('start').get('month'),
                                       ex.get('dateRange').get('start').get('year'))
                end = '{},{}'.format(ex.get('dateRange').get('end').get('month'),
                                     ex.get('dateRange').get('end').get('year')) \
                    if len(ex['dateRange']) > 1 else '8,2020'
                tenure = self.get_tenure(start, end)
                profile['experience'].append([ex.get('title').strip() if ex.get('title') else None,
                                              ex.get('companyName').strip() if ex.get('companyName') else None,
                                              tenure,
                                              ex.get('description').strip() if ex.get('description') else None])
        for skill in skills:
            profile['skills'].append(skill.get('name').strip() if skill.get('name') else None)

        return profile

    @staticmethod
    def get_tenure(start, end):
        """

        :param start:
        :param end:
        :return:
        """
        tenure = ''
        start_month, start_year = start.split(',')
        end_month, end_year = end.split(',')
        if start_month == 'None' or end_month == 'None':
            return '{} yr(s)'.format(int(end_year) - int(start_year))
        else:
            diff_in_months = (int(end_year) - int(start_year)) * 12 + (int(end_month) - int(start_month)) + 1
            months = diff_in_months % 12
            years = math.floor(diff_in_months / 12)

            if months > 0 and years > 0:
                tenure = '{} yr(s) {} mo(s)'.format(years, months)
            elif months > 0 and years == 0:
                tenure = '{} mo(s)'.format(months)
            elif months == 0 and years > 0:
                tenure = '{} yr(s)'.format(years)
        return tenure

