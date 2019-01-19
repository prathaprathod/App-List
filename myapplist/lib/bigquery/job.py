from gitmostwanted.lib.bigquery.result import ResultJob
from gitmostwanted.lib.bigquery.service import ServiceGmw
from itertools import chain
from uuid import uuid4


class Job:
    """:type num_retries: int"""
    num_retries = 5

    def __init__(self, api: ServiceGmw, query_str: str, batch: bool = False):
        self.__complete = self.__id = False
        self.__query_str = query_str
        self.__batch = batch
        self.__api = api

    def __insert(self, query_str: str, batch: bool = False):
        body = {
            'jobReference': {
                'projectId': self.__api.project_id,
                'job_id': str(uuid4())
            },
            'configuration': {
                'query': {
                    'query': query_str,
                    'priority': 'BATCH' if batch else 'INTERACTIVE'
                }
            }
        }
        return self.__api.jobs()\
            .insert(projectId=self.__api.project_id, body=body)\
            .execute(num_retries=self.num_retries)['jobReference']['jobId']

    @property
    def id(self):
        return self.__id

    @property
    def complete(self):
        if not self.__complete:
            self.__complete = (self.info['status']['state'] == 'DONE')
        return self.__complete

    @property
    def info(self):
        if not self.id:
            raise JobNotStartedException('The job is not started yet')
        return self.__api.jobs()\
            .get(projectId=self.__api.project_id, jobId=self.id)\
            .execute(num_retries=self.num_retries)

    @property
    def results(self):
        return chain.from_iterable(self.pages)

    @property
    def pages(self):
        if not self.complete:
            raise JobIncompleteException('The job is not complete yet')

        kwargs = {'projectId': self.__api.project_id, 'jobId': self.id}
        has_next = True
        while has_next:
            response = self.__api.jobs()\
                .getQueryResults(**kwargs)\
                .execute(num_retries=self.num_retries)

            has_next = ('pageToken' in response)
            if has_next:
                kwargs['pageToken'] = response['pageToken']

            yield ResultJob(response)

    def execute(self):
        self.__id = self.__insert(self.__query_str, self.__batch)
        return self.id


class JobIncompleteException(Exception):
    pass


class JobNotStartedException(Exception):
    pass
