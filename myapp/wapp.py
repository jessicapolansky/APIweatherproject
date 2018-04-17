import requests
import json
import os
import queries
import tornado.ioloop
import tornado.web
import tornado.log
import psycopg2
import datetime
from jinja2 import \
  Environment, PackageLoader, select_autoescape
ENV = Environment(
  loader=PackageLoader('wapp', 'templates'),
  autoescape=select_autoescape(['html', 'xml'])
)

class TemplateHandler(tornado.web.RequestHandler):
  def initialize(self):
    self.session = queries.Session(
      'postgresql://postgres@localhost:5432/weather')
            
  def render_template (self, tpl, context):
    template = ENV.get_template(tpl)
    self.write(template.render(**context))
    
class MainHandler(TemplateHandler):
  def setCache(self, cacheweather):
    cacheweather = cacheweather.json()
    self.session.query('''INSERT INTO weather VALUES (
              DEFAULT, %(city)s, %(icon)s, %(description)s, 
              %(temperature)s, %(wind)s, %(direction)s, %(updated)s)
              ''', {
                  'city': cacheweather['name'],
                  'icon':'https://openweathermap.org/img/w/'+ cacheweather['weather'][0]['icon'],
                  'description':cacheweather['weather'][0]['description'],
                  'temp': cacheweather['main']['temp'],
                  'wind':cacheweather['wind']['speed'],
                  'direction':cacheweather['wind']['deg'],
                  'updated': datetime.datetime.utcnow()
      })
  def setContext(self, cacheweather):
    cacheweather = cacheweather.json()
    data = {
        'city': cacheweather['name'],
        'icon': 'https://openweathermap.org/img/w/'+ cacheweather['weather'][0]['icon'],
        'description': cacheweather['weather'][0]['description'],
        'temp': cacheweather['main']['temp'],
        'wind': cacheweather['wind']['speed'],
        'direction':cacheweather['wind']['deg']
    }
    return data
  def getCache(self, db_id):
    db_entry = self.session.query('SELECT * FROM weather WHERE id = %(id)s', {'id': str(db_id)})
    data = {
        'city': db_entry[0]['city'],
        'icon': db_entry[0]['icon'],
        'description': db_entry[0]['description'],
        'temperature': db_entry[0]['temperature'],
        'wind': db_entry[0]['wind'],
        'direction':db_entry[0]['direction']
    }
    return data
  def get(self):
    self.render_template("home.html", {})
  def post (self):
    cityname = self.get_body_argument('cityname', None)
    updated = self.session.query('''
          SELECT updated, id FROM weather WHERE city=%(cityname)s ORDER BY updated DESC LIMIT 1
          ''', {'cityname':cityname})
    if (updated and (updated[0]['updated'] < datetime.datetime.utcnow() - datetime.timedelta(minutes=1))):
      data = self.getCache(updated[0]['id'])
      self.render_template("weather.html", {'data': data})
    else:
      city = {'q' : cityname, 'appid' : 'd687aa8253fff981b6801bd97704595b', 'units' : 'imperial'}
      weather = requests.get('https://api.openweathermap.org/data/2.5/weather', params = city)
      print(weather.text)
      self.render_template("weather.html", {'results': weather.json()})

class WeatherHandler(TemplateHandler):
    def get(self):
        self.set_header(
        'Cache-Control',
        'no-store, no-cache, must-revalidate, max-age=0')
        self.render_template("weather.html", {})
        
def make_app():
  return tornado.web.Application([
    (r"/", MainHandler),
    (r"/weather", WeatherHandler),
    (r"/static/(.*)", 
      tornado.web.StaticFileHandler, {'path': 'static'}),
  ], autoreload=True)
  
if __name__ == "__main__":
  tornado.log.enable_pretty_logging()
  app = make_app()
  app.listen(int(os.environ.get('PORT', '8080')))
  tornado.ioloop.IOLoop.current().start()

