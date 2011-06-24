import re
import logging
import os
import wsgiref.handlers

from google.appengine.ext import db
from google.appengine.api import urlfetch

from django.utils import simplejson as json

import tornado.wsgi
import tornado.web



class Cache(db.Model):
    json = db.TextProperty()


class Index(tornado.web.RequestHandler):
    def get(self):
        cache = Cache.get_by_key_name('cache')
        if not cache or self.get_argument('update', None):
            topic = self.fetch_topic()
            cache = Cache(key_name='cache', json=json.dumps(topic))
            cache.put()
        else:
            topic = json.loads(cache.json)
        self.render('topic.html', topic=topic, graph=json.dumps(topic['graph']))
    
    @staticmethod
    def fetch_topic():
        response = urlfetch.fetch('http://api.ihackernews.com/page', deadline=10)
        topics = json.loads(response.content)
        topic_id = str(topics['items'][0]['id'])
        
        logging.error(topic_id)
        response = urlfetch.fetch('http://api.ihackernews.com/post/' + topic_id, deadline=10)
        topic = json.loads(response.content)
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
    (r'/', Index),
], **settings)


def main():
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == "__main__":
    main()
    