#!/usr/bin/env python
# _*_ coding: utf-8 _*_
################################################################################
#
# Copyright (c) 2014 All Rights Reserved
#
################################################################################
"""
This module realizes a mini webpage spider which will crawl the urls matching 
specific pattern through the breadth priority and save the crawled webpages 
in hard disk.

Author: weileizhe
Date: 2014/11/11 00:00:06
"""

import argparse
import ConfigParser
import logging
import os
import Queue
import re
import sys
import time
import threading
import urllib2
import urlparse

import bs4

import logger_util


VERSION = '1.0'


class Error(Exception):
    """
    Base class for exception.
    """
    pass


class ConfigurationException(Error):
    """
    Configuration exception if fail to parse configuration file.
    """
    pass


class Url(object):
    """
    Url object to crawl and parse.
    
    Attributes:
        url: Url to crawl and parse.
        depth: The crawl depth of url. 
    """

    def __init__(self, url, depth=0):
        """ Init the url.
        
        Args:
            url: Url to crawl and parse.
            depth: The crawl depth of url.
        """
        self.url = url
        self.depth = depth        


class MiniSpiderThread(threading.Thread):
    """
    A mini spider thread.
    
    Attributes:
        url_queue: The url queue to crawl and parse.
        crawled_urls: The crawled urls.
        max_depth: The max crawl depth.
        crawl_interval: The crawl time interval.
        crawl_timeout: The crawl timeout.
        target_regex: The target url regular expression matching special regularation to save.
        output_directory: The output directory for saving target webpages.  
        grab_url_success: If grab url success or not.
        url_response: The response from grabing url.
    """

    def __init__(self, url_queue, crawled_urls, max_depth, crawl_interval,
                 crawl_timeout, target_url, output_directory):
        """ Init the mini spider thread.

        Args:
            url_queue: The url queue to crawl and parse.
            crawled_urls: The crawled urls.
            max_depth: The max crawl depth.
            crawl_interval: The crawl time interval.
            crawl_timeout: The crawl timeout.
            target_url: The target url matching special regularation to save.
            output_directory: The output directory for saving target webpages.            
        """
        threading.Thread.__init__(self)
        self.url_queue = url_queue
        self.crawled_urls = crawled_urls
        self.max_depth = max_depth
        self.crawl_interval = crawl_interval
        self.crawl_timeout = crawl_timeout
        self.target_regex = re.compile(target_url)
        self.output_directory = output_directory
        self.grab_url_success = False
        self.url_response = None

    def run(self):
        """
        Run crawl job.
        """
        while True:
            url_obj = self.url_queue.get(self.crawl_timeout)
            try:
                self.crawl_job(url_obj, self.url_queue, self.crawled_urls)
                time.sleep(self.crawl_interval) 
            except Error as error:
                logging.warn('Crawl %s failed due to %s', url_obj.url, str(error))
                
            self.url_queue.task_done()
           
    def crawl_job(self, url_obj, url_queue, crawled_urls):
        """
        A crawl job for crawling the url.

        Crawl the url,save the target url and put the uncrawled urls to the url_queue.

        Args:
            url_obj: The current url object for crawling and parsing.
            url_queue: The url queue to crawl and parse.
            crawled_urls: A set for urls already crawled.
        """
        self.grab_url(url_obj.url)
        if not self.grab_url_success:
            logging.info('Grab url %s failed', url_obj.url)
            return

        if self.target_regex.match(url_obj.url) is not None:
            self.save_specific_webpage(url_obj.url, self.output_directory)

        for next_url in self.iterate_next_urls(url_obj):
            if mutex.acquire(1) and next_url not in crawled_urls:
                crawled_urls.add(next_url)
                next_url_obj = Url(next_url, url_obj.depth + 1)
                url_queue.put(next_url_obj)
            mutex.release()
    
    def grab_url(self, url):
        """
        Grab the url

        Args:
            url: The current url for crawling and parsing. 
        """
        try:
            self.url_response = urllib2.urlopen(url, timeout=self.crawl_timeout)
            if self.url_response.getcode() == 200:
                self.grab_url_success = True
            else:
                logging.info('Fail to grab "%s" with status code %s',
                    url, self.url_response.getcode())
                self.grab_url_success = False
        except urllib2.HTTPError as ex:
            self.grab_url_success = False
            logging.warn(str(ex.code))
            return
        except urllib2.URLError as ex:
            self.grab_url_success = False
            logging.warn(str(ex.reason))
            return
        else:
            pass

    def save_specific_webpage(self, url, output_directory):
        """
        Save webpage matching the specific pattern to output_directory.
        
        Args:
            url: The current url for crawling and parsing.
            output_directory: Output directory for saving target webpages.  
        """
        if not self.grab_url_success:
            return
        file_name = urllib2.quote(url, '')
        target_path = os.path.join(output_directory, file_name)
        target_directory = os.path.dirname(target_path)
        if not os.path.exists(target_directory):
            os.makedirs(target_directory)
        with open(target_path, 'wb') as target_file:
            target_file.write(self.url_response.read())

    def iterate_next_urls(self, url_obj):
        """
        Iterate next urls in current webpage.
        """
        if not self.grab_url_success:
            logging.warn('Grab url %s failed or not started.', url_obj.url)
            return
 
        content_type = self.url_response.info().gettype() 
        if content_type == 'text/html'  and \
            url_obj.depth < self.max_depth:
            webpage_urls = self._iterate_webpage_urls(self.url_response.read())
            url_join_function = lambda u: self.url_join(url_obj.url, u)
            webpage_urls = map(url_join_function, webpage_urls)
            for url in webpage_urls:
                yield url

    def url_join(self, base, url):
        """
        Join urls.
        """
        joined_url = urlparse.urljoin(base, url)
        splited_url = urlparse.urlsplit(joined_url)
        path = os.path.normpath(splited_url.path)
        return urlparse.urlunsplit((splited_url.scheme, splited_url.netloc,
                                    path, splited_url.query,
                                    splited_url.fragment))

    def _iterate_webpage_urls(self, webpage_content):
        """
        Iterate webpage urls
        """
        soup = bs4.BeautifulSoup(webpage_content)
        element_attribution_map = {
            'a': 'href',
            'link': 'href',
            'script': 'src',
            'img': 'src',
        }

        for element, attribution in element_attribution_map.iteritems():
            for url in self._find_urls_of_element(soup, element, attribution):
                yield url

    def _find_urls_of_element(self, soup, element_name, attribution_name):
        """
        Find urls of elements.
        """
        elements = soup.find_all(element_name)
        for element in elements:
            try:
                url = element[attribution_name]
                if self._is_valid_url(url):
                    yield url
            except KeyError:
                logging.debug('Attribution %s of element %s not found',
                            attribution_name, element_name)

    def _is_valid_url(self, url):
        """
        Judge if url is valid or not.
        """
        if url.startswith('javascript:'):
            return False

        return True


def parse_configuration(configuration_file_name):
    """
    Parse configuration file.

    Args:
        configuration_file_name: Configuration file name (include path) to parse.

    Returns:
        A ConfigParser object.

    Raises:
        ConfigurationException: Fail to parse configuration file.
    """
    default_configuration = {
        'url_list_file': './urls',
        'output_directory': './output',
        'max_depth': '1',
        'crawl_interval': '1',
        'crawl_timeout': '1',
        'target_url': '.*\.(gif|png|jpg|bmp)$',
        'thread_count': '8'
    }

    configuration = ConfigParser.ConfigParser(default_configuration)
    configuration.add_section('spider')
    configuration.read(configuration_file_name)

    if not os.path.exists(configuration.get('spider', 'url_list_file')):
        raise ConfigurationException('Url list file not found!')

    output_directory = configuration.get('spider', 'output_directory')
    if not os.path.exists(output_directory):
        os.makedirs(os.path.abspath(output_directory))

    if configuration.getint('spider', 'max_depth') < 0:
        raise ConfigurationException('The max crawling depth configuration max_depth' 
                                     'must be no less than zero.')

    if configuration.getint('spider', 'crawl_interval') <= 0:
        raise ConfigurationException('The crawling time interval configuration crawl_interval'
                                     'must be greater than zero.')

    if configuration.getint('spider', 'crawl_timeout') <= 0:
        raise ConfigurationException('The crawling timeout configuration crawl_timeout'
                                     'must be greater than zero.')

    if configuration.getint('spider', 'thread_count') < 1:
        raise ConfigurationException('The crawling thread count configuration thread_count'
                                     'must be greater than zero.')

    return configuration

    
def argument_parser():
    """
    Parse the arguments from cmd line.

    Returns:
        arguments: Arguments from cmd line.
    """
    argument_parser = argparse.ArgumentParser(description='A mini spider.')
    argument_parser.add_argument('-c', '--conf',
                                 default="spider.conf",
                                 help='confiuration file path(default is "spider.conf")')
    argument_parser.add_argument('-v', '--version',
                                 action='version',
                                 version='%(prog)s: ' + VERSION)
    arguments = argument_parser.parse_args()

    return arguments 


def run_spider(configuration):
    """
    Run spider and start crawling urls.
    
    Args:
        configuration: The configuration of mini spider.
    """
    url_queue = Queue.Queue()
    crawled_urls = set()
    
    thread_count = configuration.getint('spider', 'thread_count')
    max_depth = configuration.getint('spider', 'max_depth') 
    crawl_interval = configuration.getint('spider', 'crawl_interval') 
    crawl_timeout = configuration.getint('spider', 'crawl_timeout') 
    target_url = configuration.get('spider', 'target_url')
    output_directory = configuration.get('spider', 'output_directory')

    
    with open(configuration.get('spider', 'url_list_file'), 'r') as url_lines:
        for line in url_lines:
            url = line.rstrip()
            url_obj = Url(url, 0)
            url_queue.put(url_obj)

    for i in xrange(configuration.getint('spider', 'thread_count')):
        spider_thread = MiniSpiderThread(url_queue, crawled_urls, max_depth, crawl_interval, 
                                         crawl_timeout, target_url, output_directory)
        spider_thread.setDaemon(True)
        spider_thread.start()

    url_queue.join()


def init_log():
    """
    Init logging for mini spider.
    """
    logger_util.init_logger(os.path.join(os.path.abspath(os.curdir), 'log'))

mutex = threading.Lock()
def main():
    """
    Main function entrace.
    """
    init_log()
    arguments = argument_parser()
    try:
        configuration = parse_configuration(arguments.conf) 
    except ConfigurationException as ex:
        logging.error(str(ex))
        return -1
    run_spider(configuration)

if __name__ == '__main__':
    main()    

