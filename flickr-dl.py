#!/usr/bin/env python
#-*- coding:utf-8 -*-
'''
Created on 2011-11-12

@author: "Yang Junyong <yanunon@gmail.com>"
'''

import random
import re
import os
import time
import urllib2
import flickr
import datetime
from threading import Thread, Lock


class UrlFetcher(object):
    
    user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/535.7 (KHTML, like Gecko) Chrome/16.0.904.0 Safari/535.7'

    def __init__(self, http_proxy=None):
        self.http_proxy = http_proxy
        self.headers = {'User-Agent' : self.user_agent}
        
        if http_proxy:
            urllib2.install_opener(urllib2.build_opener(urllib2.ProxyHandler(self.http_proxy)))
        
    def do_fetch(self, url):
        req = urllib2.Request(url=url, headers=self.headers)
        try:
            rsp = urllib2.urlopen(req)
            return rsp.read()
        except:
            return None

class DownloadPhoto(object):

    def __init__(self, save_dir=None, http_proxy=None):
        self.fetcher = UrlFetcher(http_proxy=http_proxy)
        self.save_dir = save_dir
        
    def download(self, photo):
        msg = ''
        try:
            photo_large_url = photo.getLarge()
        except Exception, e:
            msg = 'Error:%s' % e
            return msg
        photo_name = photo_large_url[photo_large_url.rfind('/')+1:]
        photo_path = os.path.join(self.save_dir, photo_name)
        if os.path.exists(photo_path):
            msg = 'Path Exist:%s' % photo_path
            return msg
        
        photo_data = self.fetcher.do_fetch(photo_large_url)
        
        try:
            photo_file = open(photo_path, 'wb')
            photo_file.write(photo_data)
            photo_file.close()
        except Exception, e:
            msg = 'Error:%s,in:%s' % (e, photo_large_url)
        else:
            msg = 'Finish:%s' % photo_path
        
        return msg
            

class TaskQueue:
    
    def __init__(self):
        self.stack = []
        self.lock = Lock()
        self.join_lock = Lock()
        self.length = 0
        self.stop_all = False
        self.unfinished = 0
        self.finished = 0
        
    def get(self):
        task = -1
        self.lock.acquire()
        try:
            if self.length > 0:
                task = self.stack.pop()
                self.length -= 1
            elif self.stop_all:
                task = None
        finally:
            self.lock.release()
        
#        self.join_lock.acquire()
#        try:
#            if self.stop_all:
#                task = None
#        finally:
#            self.join_lock.release()
            
        return task
    
    def put(self, task):
        self.lock.acquire()
        try:
            self.stack.append(task)
            self.length += 1
            self.unfinished += 1
        finally:
            self.lock.release()
    
    def put_list(self, task_list):
        self.lock.acquire()
        try:
            self.stack.extend(task_list)
            self.length += len(task_list)
            self.unfinished += len(task_list)
        finally:
            self.lock.release()
    
    def get_size(self):
        length = -1
        self.lock.acquire()
        try:
            length = self.length
        finally:
            self.lock.release()
        return length
    
    def finish_one(self, msg):
        
        self.lock.acquire()
        try:
            self.unfinished -= 1
            self.finished += 1
            print '[%d] %s' % (self.finished, msg)
        finally:
            self.lock.release()
        
        
    def join(self):
        self.lock.acquire()
        try:
            while self.unfinished > 0:
                self.lock.release()
                time.sleep(0.1)
                self.lock.acquire()
        finally:
            self.lock.release()
    
    def stop(self):
        self.join()
        self.lock.acquire()
        try:
            self.stop_all = True
            self.length = 0
        finally:
            self.lock.release()
        
    
class DownloadThread(Thread):
    
    def __init__(self, task_queue, photo_dir, name=None):
        Thread.__init__(self, name=name)
        self.downloader = DownloadPhoto(photo_dir)
        self.task_queue = task_queue
        
    def run(self):
        while True:
            photo = self.task_queue.get()
            
            if photo is None:
                return
            elif photo == -1:
                time.sleep(0.1)
                continue

            msg = self.downloader.download(photo)
            self.task_queue.finish_one(msg)

class FlickrDL:
    
    def __init__(self, photo_dir, thread_num=5):
        self.task_queue = TaskQueue()
        self.threads = []
        self.thread_num = thread_num
        for i in range(self.thread_num):
            thread = DownloadThread(self.task_queue, photo_dir, '[%d]' % i)
            self.threads.append(thread)
            thread.start()
            
    def dl_photos(self, count):
        times = (count + 499) / 500
        start_day = datetime.date(2012,2,10)
        delta = datetime.timedelta(days=1)
        for t in range(times):
            date = (start_day - delta * t).strftime("%Y-%m-%d")
            try:
                photos = flickr.interestingness(date, 1, 500) 
                #self.task_queue.put_list(photos)
            except Exception,e:
                print e
            else:
                self.task_queue.put_list(photos)
    
    def wait_thread_done(self):
        self.task_queue.join()
    
    def stop_all(self):
        self.task_queue.stop()
        for thread in self.threads:
            thread.join()
            
if __name__ == '__main__':
    #d = downloadMap('gmap')
    d = FlickrDL('./photos', 10)
    
    d.dl_photos(2000)
    d.wait_thread_done()
    d.stop_all()
#    for thread in d.threads:
#        thread.join()
    
    
