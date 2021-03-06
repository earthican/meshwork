import re, boto, gzip, warc, os, time, sys
from urlparse import urlparse
from collections import Counter
from boto.s3.key import Key
from gzipstream import GzipStreamFile

from pyspark import SparkContext, SparkConf

def get_links(data):
    links = re.findall(r'href=[\'"]?([^\'" >]+)', data)
    try:
        links = set(map(lambda link: urlparse(link).netloc, links))
        return [l.lower().replace('www.', '') for l in links if l]
    except ValueError:
        return None

def process_record(record):
    if record['Content-Type'] == 'application/http; msgtype=response':
        payload = record.payload.read()
        headers, body = payload.split('\r\n\r\n', 1)
        if 'Content-Type: text/html' in headers:
            url = urlparse(record['WARC-Target-URI']).netloc.replace('www.', '')
            links = get_links(body)
            if links:
                return url, links
    return None, None

def extract_links(path):
    link_edges = []
    conn = boto.connect_s3(anon=True)
    bucket = conn.get_bucket('aws-publicdatasets')
    key = Key(bucket, path)
    warc_file = warc.WARCFile(fileobj=GzipStreamFile(key))
    for record in warc_file:
        if record['Content-Type'] == 'application/http; msgtype=response':
            url, links = process_record(record)
            if links:
                for link in links:
                    link_edges.append('{} {}'.format(url, link))
    return link_edges

def main():
    link_edges_file_path = 'hdfs://{}:9000/data/link-edges'.format(os.environ['HADOOP_IP'])
    conf = SparkConf().setAppName('ExtractCCLinks')
    sc = SparkContext(conf=conf)
    warc_paths_file_path = 'hdfs://{}:9000/data/warc-paths/warc-100.paths'.format(os.environ['HADOOP_IP'])
    warc_paths = sc.textFile(warc_paths_file_path)
    link_edges = warc_paths.map(extract_links).flatMap(lambda line: line)
    print link_edges.count()
    print link_edges.take(10)
    # Delete existing /data/link-edges directory...
    os.system('hdfs dfs -rm -r -f /data/link-edges')
    link_edges.saveAsTextFile(link_edges_file_path)

if __name__ == '__main__':
    main()
