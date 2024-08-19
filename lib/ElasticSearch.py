from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
import yaml
import math
import requests


class ElasticSearch:
    def __init__(self):
        config = yaml.load(open('config.yaml'), Loader=yaml.FullLoader)['ElasticSearch']
        host = config['host']
        port = str(config['port'])
        account = config['account']
        password = config['password']
        self.es = Elasticsearch(host=host, port=port, http_auth=(account, password), timeout=60, max_retries=5, retry_on_timeout=True)

    def get_search_result(self, service_ID, tf_number, start_time, end_time, call_type):
        query_column = 'toNumber'
        if call_type == 'outbound':
            query_column = 'fromNumber'

        # start_time = '2023-08-04T01:00:00Z'
        # end_time = '2023-08-04T02:00:00Z'
        s = Search(using=self.es, index='cdr*').filter('range', **{'createTime': {'gt': f'{start_time}', 'lte': f'{end_time}'}})
        s = s.query('bool', must=[
            {'match': {'serviceId': service_ID}},
            {'match': {query_column: tf_number}},
            {'match': {'callDirection': call_type}},
            {'match': {'cdrType': 'call'}}
        ])
        s = s[:10000]

        response = s.execute()
        documents = response["hits"]["hits"]
        print(documents)
        usage = 0
        for doc in documents:
            call = doc['_source'].to_dict()
            duration_minute = math.ceil(call['duration'] / 60)
            usage += duration_minute
            print(doc['_source'].to_dict())

        print('total call:', len(documents))
        print(usage)

    # def get_index(self):
    #     url = f'https://{self.host}:9200/_aliases'
    #     s = requests.Session()
    #     response = s.get(url, auth=(self.account, self.password))
    #     print(response.json())

    def get_tf_usage(self, service_ID, tf_number, start_time, end_time, call_type):
        query_column = 'toNumber'
        if call_type == 'outbound':
            query_column = 'fromNumber'
        start_time = start_time.strftime('%Y-%m-%dT%H:%M:%S.%f')
        end_time = end_time.strftime('%Y-%m-%dT%H:%M:%S.%f')
        s = Search(using=self.es, index='cdr*').filter('range', **{'createTime': {'gt': f'{start_time}', 'lte': f'{end_time}'}})
        s = s.query('bool', must=[
            {'match': {'serviceId': service_ID}},
            {'match': {query_column: tf_number}},
            {'match': {'callDirection': call_type}},
            {'match': {'cdrType': 'call'}}
        ])
        s = s[:5000]
        response = s.execute()
        documents = response["hits"]["hits"]
        usage = 0
        for doc in documents:
            call = doc['_source'].to_dict()
            duration_minute = math.ceil(call['duration']/60)
            usage += duration_minute

        # usage = random.randint(1, 10)     # fake random usage when testing

        return usage

