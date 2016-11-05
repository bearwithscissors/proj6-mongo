"""
Flask web app connects to Mongo database.
Keep a simple list of dated memoranda.

Representation conventions for dates:
   - We use Arrow objects when we want to manipulate dates, but for all
     storage in database, in session or g objects, or anything else that
     needs a text representation, we use ISO date strings.  These sort in the
     order as arrow date objects, and they are easy to convert to and from
     arrow date objects.  (For display on screen, we use the 'humanize' filter
     below.) A time zone offset will
   - User input/output is in local (to the server) time.
"""

import flask
from flask import g
from flask import render_template
from flask import request
from flask import url_for

import json
import logging

# Date handling
import arrow    # Replacement for datetime, based on moment.js
# import datetime # But we may still need time
from dateutil import tz  # For interpreting local times

# Mongo database
from pymongo import MongoClient
import pymongo
# for use removing _ids
from bson.objectid import ObjectId
import secrets.admin_secrets
import secrets.client_secrets
MONGO_CLIENT_URL = "mongodb://{}:{}@localhost:{}/{}".format(
    secrets.client_secrets.db_user,
    secrets.client_secrets.db_user_pw,
    secrets.admin_secrets.port,
    secrets.client_secrets.db)

###
# Globals
###
import CONFIG
app = flask.Flask(__name__)
app.secret_key = CONFIG.secret_key

####
# Database connection per server process
###

try:
    dbclient = MongoClient(MONGO_CLIENT_URL)
    db = getattr(dbclient, secrets.client_secrets.db)
    collection = db.dated

except:
    print("Failure opening database.  Is Mongo running? Correct password?")
    sys.exit(1)



###
# Pages
###

@app.route("/")
@app.route("/index")
def index():
  app.logger.debug("Main page entry")
  g.memos = get_memos()
  for memo in g.memos:
      app.logger.debug("Memo: " + str(memo))
  return flask.render_template('index.html')


# We don't have an interface for creating memos yet
@app.route("/create")
def create():
    app.logger.debug("Create")
    return flask.render_template('create.html')


@app.route("/_add_memo")
def add_memo():
    '''
    Submits a memo and date to the database after form submission.
    '''
    app.logger.debug("Add Memo")
    date = request.args.get('date', 0, type=str)
    split_date = date.split("/")

    m = int(split_date[0])
    d = int(split_date[1])
    y = int(split_date[2])

    #app.logger.debug("date:"+date)
    date = arrow.get(y,m,d).isoformat()
    #app.logger.debug("date:"+date)
    memo = request.args.get('memo', 0, type=str)
    #app.logger.debug("memo:"+memo)
    test = {"type":"dated_memo","date": date,"text": memo }
    collection.insert(test)
    return flask.render_template('index.html')

@app.route("/_remove_memo")
def remove_memo():
    '''
    Removes one specified _id from the database
    '''
    _id = request.args.get('_id', 0, type=str)
    app.logger.debug("_id:"+_id)
    collection.delete_one({"_id": ObjectId(_id)})
    return flask.render_template('index.html')

@app.errorhandler(404)
def page_not_found(error):
    app.logger.debug("Page not found")
    return flask.render_template('page_not_found.html',
                                 badurl=request.base_url,
                                 linkback=url_for("index")), 404

#################
#
# Functions used within the templates
#
#################


@app.template_filter( 'humanize' )
def humanize_arrow_date( date ):
    """
    Date is internal UTC ISO format string.
    Output should be "today", "yesterday", "in 5 days", etc.
    Arrow will try to humanize down to the minute, so we
    need to catch 'today' as a special case.
    """
    try:
        then = arrow.get(date).to('local')
        now = arrow.utcnow().to('local')
        #Despite accurate dates, 'now' is off by one day for me so I increment 1 day
        now = now.replace(days=+1)
        if then.date() == now.date():
            human = "Today"
        else:
            human = then.humanize(now)
            if human == "in a day":
                human = "Tomorrow"
    except:
        human = date
    return human


#############
#
# Functions available to the page code above
#
##############
def get_memos():
    """
    Returns all memos in the database, in a form that
    can be inserted directly in the 'session' object.
    """
    records = [ ]
    for record in collection.find( { "type": "dated_memo" } ).sort("Date", pymongo.DESCENDING):
        record['date'] = arrow.get(record['date']).isoformat()
        records.append(record)
    #sorts records to be displayed by date
    records = sorted(records, key=lambda k: k['date'], reverse=True)
    return records


if __name__ == "__main__":
    app.debug=CONFIG.DEBUG
    app.logger.setLevel(logging.DEBUG)
    app.run(port=CONFIG.PORT,host="0.0.0.0")
