import re
import logging
import urllib
import os
import wsgiref.handlers

from google.appengine.api import memcache
import simplejson as json

import tornado.wsgi
import tornado.web



class Topics(tornado.web.RequestHandler):
    def get(self):
        topics = memcache.get('topics')
        if topics is None:
            try:
                response = urllib.urlopen('http://api.ihackernews.com/page').read()
                data = json.loads(response)
            except Exception, e:
                logging.error(e)
                return self.render('error.html')
            topics = data['items']
            memcache.add('topics', topics, 10)
        self.render('topics.html', topics=topics)


class Topic(tornado.web.RequestHandler):
    def get(self, id):
        topic = memcache.get('topic:' + id)
        if topic is None:
            try:
                topic = self.fetch_topic(id)
            except Exception, e:
                logging.error(e)
                return self.render('error.html')
            memcache.add('topic:' + id, topic, 10)
        self.render('topic.html', topic=topic)
        
    @staticmethod
    def fetch_topic(id):
        response = urllib.urlopen('http://api.ihackernews.com/post/' + id).read()
        topic = json.loads(response)
        topic['graph'] = {}
        topic['all_comments'] = []
        
        def generate_graph(comments):
            """Generates an id mapping between comments and their children.
            This graph is used for javascript layout.
                {
                    "comment_id": ["child_id", "child_id2"],
                    "comment_id2": ...
                }
            """
            for comment in comments:
                topic['all_comments'].append(comment)
                parent = topic['graph'].setdefault(comment['parentId'], [])
                parent.append(comment['id'])
                generate_graph(comment['children'])
        
        generate_graph(topic['comments'])
        return topic


settings = {
    'template_path': os.path.join(os.path.dirname(__file__), 'templates'),
    'debug': os.environ['SERVER_SOFTWARE'].startswith('Dev')
}
application = tornado.wsgi.WSGIApplication([
    (r'/', Topics),
    (r'/(.+)', Topic)
], **settings)


def main():
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == "__main__":
    main()
    