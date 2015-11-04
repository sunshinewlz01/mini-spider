#!/usr/bin/env python
# _*_ coding: utf-8 _*_
################################################################################
#
# Copyright (c) 2014 Baidu.com, Inc. All Rights Reserved
#
################################################################################
"""
This module realizes unit test for mini spider.

Author: weileizhe(weileizhe@baidu.com)
Date: 2014/11/12 00:00:06
"""

import httpretty
import os
import Queue
import shutil
import unittest


import mini_spider


class TestParseConfiguration(unittest.TestCase):
    """ Test parse_configuration(configuration_file_name) function.
    """

    def setUp(self):
        """ Set up test.
        """
        self.configuration_file_path = 'test.conf'

    def tearDown(self):
        """ Tear down test.
        """
        if os.path.exists(self.configuration_file_path):
            os.remove(self.configuration_file_path)

    def write_configuration_file(self, content):
        """ Write content to configuration file.
        
        Args:
            content: The content of configuration file.
        """
        with open(self.configuration_file_path, 'w') as configuration_file:
            configuration_file.write(content)

    def test_normal_configuration(self):
        """ Test for normal configuration file parse.
        """
        self.write_configuration_file(
            '[spider]\n'
            'url_list_file: ./urls\n'
            'output_directory: ./output\n'
            'max_depth: 6\n'
            'crawl_interval: 1\n'
            'crawl_timeout: 5\n'
            'target_url: .*\.(gif|png|jpg|bmp)$\n'
            'thread_count: 8\n'
        )

        configuration = mini_spider.parse_configuration(self.configuration_file_path)
        self.assertEqual(configuration.get('spider', 'url_list_file'), './urls')
        self.assertEqual(configuration.get('spider', 'output_directory'), './output')
        self.assertEqual(configuration.getint('spider', 'max_depth'), 6)
        self.assertEqual(configuration.getint('spider', 'crawl_interval'), 1)
        self.assertEqual(configuration.getint('spider', 'crawl_timeout'), 5)
        self.assertEqual(configuration.getint('spider', 'thread_count'), 8)
        self.assertEqual(configuration.get('spider', 'target_url'), '.*\.(gif|png|jpg|bmp)$')

    def test_partly_default_configuration(self):
        """ Test for partly default configuration file parse.
        """
        self.write_configuration_file(
            '[spider]\n'
            'max_depth: 10\n'
            'crawl_interval: 2\n'
            'crawl_timeout: 10\n'
            'target_url: .*\.(com|cn|net)$\n'
        )
        configuration = mini_spider.parse_configuration(self.configuration_file_path)
        self.assertEqual(configuration.get('spider', 'url_list_file'), './urls')
        self.assertEqual(configuration.get('spider', 'output_directory'), './output')
        self.assertEqual(configuration.getint('spider', 'max_depth'), 10)
        self.assertEqual(configuration.getint('spider', 'crawl_interval'), 2)
        self.assertEqual(configuration.getint('spider', 'crawl_timeout'), 10)
        self.assertEqual(configuration.getint('spider', 'thread_count'), 8)
        self.assertEqual(configuration.get('spider', 'target_url'), '.*\.(com|cn|net)$')

    def test_fully_default_configuration(self):
        """ Test for fully default configuration file parse.
        """
        configuration = mini_spider.parse_configuration(self.configuration_file_path)
        self.assertEqual(configuration.get('spider', 'url_list_file'), './urls')
        self.assertEqual(configuration.get('spider', 'output_directory'), './output')
        self.assertEqual(configuration.getint('spider', 'max_depth'), 1)
        self.assertEqual(configuration.getint('spider', 'crawl_interval'), 1)
        self.assertEqual(configuration.getint('spider', 'crawl_timeout'), 1)
        self.assertEqual(configuration.getint('spider', 'thread_count'), 8)
        self.assertEqual(configuration.get('spider', 'target_url'), '.*\.(gif|png|jpg|bmp)$')

    def test_invalid_max_depth_configuration(self):
        """ Test for invalid max_depth configuration parse.
        """
        self.write_configuration_file(
            '[spider]\n'
            'max_depth: -1\n'
        ) 
        with self.assertRaises(mini_spider.ConfigurationException):
            mini_spider.parse_configuration(self.configuration_file_path)

    def test_invalid_crawl_interval_configuration(self):
        """ Test for invalid crawl_interval configuration parse.
        """
        self.write_configuration_file(
            '[spider]\n'
            'crawl_interval: 0\n'
        ) 
        with self.assertRaises(mini_spider.ConfigurationException):
            mini_spider.parse_configuration(self.configuration_file_path)
    
    def test_invalid_crawl_timeout_configuration(self):
        """ Test for invalid crawl_timeout configuration parse.
        """
        self.write_configuration_file(
            '[spider]\n'
            'crawl_timeout: 0\n'
        ) 
        with self.assertRaises(mini_spider.ConfigurationException):
            mini_spider.parse_configuration(self.configuration_file_path)

    def test_invalid_thread_count_configuration(self):
        """ Test for invalid thread_count configuration parse.
        """
        self.write_configuration_file(
            '[spider]\n'
            'thread_count: 0\n'
        ) 
        with self.assertRaises(mini_spider.ConfigurationException):
            mini_spider.parse_configuration(self.configuration_file_path)


class TestMiniSpiderThread(unittest.TestCase):
    """ Test for MiniSpiderThread.
    """
    def setUp(self):
        """ Set up test.
        """
        self.url_queue = Queue.Queue()
        self.crawled_urls = set()
        self.mini_spider_thread = mini_spider.MiniSpiderThread(self.url_queue, self.crawled_urls,
                                                          6, 2, 5, '.*\.(gif|png|jpg|bmp)$', 
                                                          './output_test')
        self.url_obj = mini_spider.Url('http://example.com/iterate_next_urls/html_webpage',
                                       0)
        httpretty.enable()
        httpretty.register_uri(httpretty.GET,
                               'http://example.com/graburl/success', body = 'Grab url success.')
        httpretty.register_uri(httpretty.GET,
                               'http://example.com/graburl/fail', status = 404) 
        httpretty.register_uri(httpretty.GET,
                               'http://example.com/savewebpage/saved.txt',
                               body = 'Saved webpage content.')
        httpretty.register_uri(httpretty.GET,
                               'http://example.com/iterate_next_urls/html_webpage',
                               content_type = 'text/html',
                               body = '<a href="/test/test1.html">Link</a>\
                               <img src="/test/test3.png" /><script src="/test/test4.js"></script>')
        httpretty.register_uri(httpretty.GET,
                               'http://example.com/iterate_next_urls/not_html_webpage',
                               content_type = 'text/plain',
                               body = '/test/not_html.txt')

    def tearDown(self):
        """ Tear down test.
        """
        httpretty.disable()
        httpretty.reset()
        if os.path.exists('output_test'):
            shutil.rmtree('output_test')

    def test_grab_url_success(self):
        """ Test grabing url success.
        """
        self.mini_spider_thread.grab_url('http://example.com/graburl/success')
        self.assertTrue(self.mini_spider_thread.grab_url_success)
        self.assertEqual(self.mini_spider_thread.url_response.read(), 'Grab url success.')

    def test_grab_url_fail(self):
        """ Test grabing url fail.
        """
        self.mini_spider_thread.grab_url('http://example.com/graburl/fail')
        self.assertFalse(self.mini_spider_thread.grab_url_success)
    
    def test_save_specific_webpage(self):
        """ Test saving specific webpage.
        """
        self.mini_spider_thread.grab_url('http://example.com/savewebpage/saved.txt')
        self.mini_spider_thread.grab_url_success = True
        self.mini_spider_thread.save_specific_webpage('http://example.com/savewebpage/saved.txt',
                                                      self.mini_spider_thread.output_directory)
        saved_path = os.path.join(self.mini_spider_thread.output_directory,
                                  'http%3A%2F%2Fexample.com%2Fsavewebpage%2Fsaved.txt')
        self.assertTrue(os.path.exists(saved_path))
        with open(saved_path, 'r') as saved_file:
            self.assertEqual(saved_file.read(), 'Saved webpage content.')

    def test_iterate_next_urls_html(self):
        """ Test interate next urls for html type webpage.
        """
        self.mini_spider_thread.grab_url('http://example.com/iterate_next_urls/html_webpage')
        self.assertTrue(self.mini_spider_thread.grab_url_success)
        self.assertEqual(list(self.mini_spider_thread.iterate_next_urls(self.url_obj))[0],
                         'http://example.com/test/test1.html')

    def test_iterate_next_urls_not_html(self):
        """ Test iterate next urls for not html type webpage.
        """
        self.mini_spider_thread.grab_url('http://example.com/iterate_next_urls/not_html_webpage') 
        self.assertTrue(self.mini_spider_thread.grab_url_success)
        self.assertEqual(len(list(self.mini_spider_thread.iterate_next_urls(self.url_obj))), 0)   


def main():
    """ Main function entrance.
    """
    unittest.main()

if __name__ == '__main__':
    main()
