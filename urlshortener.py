import os
import re
import wsgiref.handlers
import datetime

from baseconvert import baseconvert, BASE10, BASE92

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

from django.utils import simplejson


class URL(db.Model):
    id = db.IntegerProperty(required=True)
    url = db.StringProperty(required=True)
    hits = db.IntegerProperty(required=True, default=0)

    is_flagged = db.BooleanProperty(required=True, default=False)
    date_and_time = db.DateTimeProperty(auto_now_add=True)
    is_active = db.BooleanProperty(required=True, default=True)

    @classmethod
    def get_last_id(cls):
        """Returns the last inserted id"""

        url = db.Query(cls).order("-__key__").fetch(1)

        return 0 if len(url) == 0 else url[0].id

    @classmethod
    def exists(cls, url):
        """Return an URL object with the given url if not None"""
        return db.Query(cls).filter('url =', url).get()

    @classmethod
    def verify(cls, url):
        """Verify the url syntax"""
        #pattern = "(https?://([-\w\.]+)+(:\d+)?(/([-\w/_\.]*(\?\S+)?)?)?)"
        # Taken from Django Forms
        pattern = re.compile(
            r'^https?://' # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|' #domain...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
            r'(?::\d+)?' # optional port
            r'(?:/?|/\S+)$', re.IGNORECASE)
        return True if re.search(pattern, url) else False


class ShortURL(db.Model):
    keyword = db.StringProperty(required=True)
    url = db.ReferenceProperty(URL)
    is_default = db.BooleanProperty(required=True, default=True)
    date_added = db.DateTimeProperty(required=True, auto_now_add=True)
    last_access = db.DateTimeProperty() 

    def new_url(self):
        return 'http://wy.pe/%s' % self.keyword

    @classmethod
    def exists(cls, keyword):
        return db.Query(cls).filter('keyword =', keyword).get()


class Index(webapp.RequestHandler):

    def get(self):

        # Params
        str_url = self.request.get('url', '')
        alias = self.request.get('alias', '').replace(' ', '_')
        format = self.request.get('format', '')

        if str_url != '' and str_url.find('wy.pe') == -1:

            template_values = {}

            if str_url.find('http') != 0 and str_url.find('ftp') != 0:
                str_url = 'http://%s' % str_url

            if URL.verify(str_url):

                url =  URL.exists(str_url)

                if url is None:
                    """If url is a new one, then a shorturl must be created for
                    it"""

                    # create URL object
                    
                    
                    

                    url = URL(id=URL.get_last_id() + 1,
                              url=str_url)
                    url.put()

                    # Creating shorturl by first time
                    shorturl = ShortURL(keyword=baseconvert(url.id, BASE10, BASE92))
                    shorturl.url = url
                    shorturl.put()
                    
                    
                    
                    template_values['short'] = shorturl.new_url()
     

                # If the url exists then a shorturl for it does exist, so it should
                # just verify the keyword exists wether or not 
                if alias != '':
                    shorturl = ShortURL.exists(alias)
                    if shorturl is None:
                        shorturl = ShortURL(keyword=alias)
                        shorturl.url = url
                        shorturl.is_default = False
                        shorturl.put()
                        template_values['short'] = shorturl.new_url()
                        
                        
                        
                    else:
                        
                        
                        
                        template_values['message'] = """The alias "%s" is not
                        available! Anyways, here's a short url.""" % alias
                        template_values['short'] = url.shorturl_set.\
                                                       filter('is_default =', True).\
                                                       get().new_url()
                else:
                    
                    
                    
                    template_values['short'] = url.shorturl_set.\
                                                   filter('is_default =', True).\
                                                   get().new_url()


                template_values['large'] = url.url
                template_values['large_trunc'] = url.url if len(url.url) < 51 else url.url[:46] + '...'
               
            else:
                template_values['message'] = "You gave me a wrong url!"

        elif str_url.find('wy.pe') >= 0:
            
            template_values = { 'message': 'So, you tried to shorten me!'}
        else:
            template_values = None


        if format == 'json':
            self.response.headers['Content-type'] = 'text/json'
            self.response.out.write(simplejson.dumps(
                {'url': template_values['short']}))
        elif format == 'text':
            self.response.out.write(template_values['short'])
        else:
            path = os.path.join(os.path.dirname(__file__), 'templates/index.html')
            self.response.out.write(template.render(path, template_values))



class Dispatcher(webapp.RequestHandler):
    def get(self):
        try:
            shorturl = ShortURL.exists(self.request.path[1:])
            mogging.info(shorturl)
            if shorturl is not None:
                shorturl.url.hits += 1
                shorturl.last_access = datetime.datetime.now()
                shorturl.url.put()
                shorturl.put()
                self.redirect(shorturl.url.url)
            else:
                self.error(404)
        except:
            self.error(500)


app = webapp.WSGIApplication([
    ('/', Index), 
    ('/.*', Dispatcher)], debug=True)


def main():
    wsgiref.handlers.CGIHandler().run(app)


if __name__ == '__main__':
    main()
