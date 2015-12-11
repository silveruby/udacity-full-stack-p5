# Import general modules
import os
import random
import string
import datetime
import httplib2
import urllib
import json
import dicttoxml
import requests

# Import modules for Flask web framework
from flask import Flask, render_template, url_for, \
    request, redirect, flash, jsonify, make_response
from flask import session as login_session

# Import extension for CSRF
from flask.ext.seasurf import SeaSurf

# Import modules for OAuth
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError

# Import modules for SQL Alchemy database
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item, User, Comment

# Setup file imports
from werkzeug import secure_filename
from flask import send_from_directory

# Setup file upload folder
UPLOAD_FOLDER = '/var/www/catalog/catalog/static/uploads/'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

# Connect to Database
engine = create_engine('postgresql://catalog:catalog@localhost/catalogdb')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
db_session = DBSession()

# Setup App
app = Flask(__name__)
csrf = SeaSurf(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# User Helper Functions
def createUser(login_session):
    newUser = User(
                username=login_session['username'],
                email=login_session['email'],
                picture=login_session['picture'])
    db_session.add(newUser)
    db_session.commit()
    user = db_session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = db_session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = db_session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


def isLoggedIn():
    if 'email' in login_session:
        return True
    return False


def hasAuthorization():
    if 'email' in login_session:

        # Load emails that are authorized to modify categories and items
        authorized_users = json.loads(
            open('/var/www/catalog/catalog/authorized_users.json', 'r').read())['authorized_users']

        # If login email is authorized, then allow them to POST
        if login_session['email'] in authorized_users:
            return True

    return False


def isUsersComment(comment_id):
    comment = db_session.query(Comment).filter_by(id=comment_id).one()
    if 'user_id' in login_session:
        if comment.user_id == login_session['user_id']:
            return True
    return False


# Upload image helpers
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],
                               filename)


# Routers
@app.route('/')
def showCatalog():
    categories = db_session.query(Category).order_by(Category.name).all()
    return render_template(
                'index.html',
                categories=categories,
                login_session=login_session)


@app.route('/new', methods=['GET', 'POST'])
def newCategory():

    if not hasAuthorization():
        return redirect(url_for('showLogin'))

    # POST
    if request.method == 'POST':
        new_category = Category(
            name=request.form['category'],
            user_id=login_session['user_id'])
        db_session.add(new_category)
        db_session.commit()
        flash("New category created")
        return redirect(url_for('showCatalog'))
    # GET
    else:
        return render_template(
                    'newCategory.html',
                    login_session=login_session)


@app.route('/category/<int:category_id>')
def showCategory(category_id):
    category = db_session.query(Category).filter_by(id=category_id).one()
    items = db_session.query(Item).filter_by(category_id=category_id).all()
    return render_template(
                'showCategory.html',
                category=category,
                items=items,
                login_session=login_session)


@app.route('/category/<int:category_id>/edit', methods=['GET', 'POST'])
def editCategory(category_id):

    if not hasAuthorization():
        return redirect(url_for('showLogin'))

    edit_category = db_session.query(Category).filter_by(id=category_id).one()

    # POST
    if request.method == 'POST':
        edit_category.name = request.form['category']
        db_session.add(edit_category)
        db_session.commit()
        flash("Category name successfully edited")
        return redirect(url_for('showCategory', category_id=category_id))
    # GET
    else:
        return render_template(
                    'editCategory.html',
                    category=edit_category,
                    login_session=login_session)


@app.route('/category/<int:category_id>/delete', methods=['GET', 'POST'])
def deleteCategory(category_id):

    if not hasAuthorization():
        return redirect(url_for('showLogin'))

    delete_category = \
        db_session.query(Category).filter_by(id=category_id).one()
    delete_items = \
        db_session.query(Item).filter_by(category_id=category_id).all()

    # POST
    if request.method == 'POST':
        db_session.delete(delete_category)
        for item in delete_items:
            db_session.delete(item)
        db_session.commit()
        flash(
            'Category ' +
            delete_category.name +
            ' and all its item(s) are deleted')
        return redirect(url_for('showCatalog'))
    # GET
    else:
        return render_template(
                        'deleteCategory.html',
                        category=delete_category,
                        login_session=login_session)


@app.route('/category/<int:category_id>/new', methods=['GET', 'POST'])
def newItem(category_id):

    if not hasAuthorization():
        return redirect(url_for('showLogin'))

    # POST
    if request.method == 'POST':

        image = request.files['photo']
        image_filename = None
        if image and allowed_file(image.filename):
            image_filename = secure_filename(image.filename)
            image.save(os.path.join(
                app.config['UPLOAD_FOLDER'],
                image_filename))

        new_item = Item(
            name=request.form['item'],
            image=image_filename,
            description=request.form['description'],
            notes=request.form['notes'],
            category_id=category_id,
            user_id=login_session['user_id'])
        db_session.add(new_item)
        db_session.commit()
        flash('New item created')
        return redirect(url_for('showCategory', category_id=category_id))
    # GET
    else:
        category = db_session.query(Category).filter_by(id=category_id).one()
        return render_template(
                    'newItem.html',
                    category=category,
                    login_session=login_session)


@app.route(
    '/category/<int:category_id>/item/<int:item_id>',
    methods=['GET', 'POST'])
def showItem(category_id, item_id):

    category = db_session.query(Category).filter_by(id=category_id).one()
    item = db_session.query(Item).filter_by(id=item_id).one()
    comments = db_session.query(Comment).filter_by(item_id=item_id).all()

    if request.method == 'POST':

        if not isLoggedIn():
            return redirect(url_for('showLogin'))

        new_comment = Comment(
                text=request.form['comment'],
                date=datetime.datetime.now(),
                item_id=item_id,
                user_id=login_session['user_id'],
                username=login_session['username']
            )
        db_session.add(new_comment)
        db_session.commit()
        flash('New comment added')
        return redirect(url_for(
                            'showItem',
                            category_id=category_id,
                            item_id=item_id))
    else:
        return render_template(
                    'showItem.html',
                    category=category,
                    item=item,
                    comments=comments,
                    login_session=login_session)


@app.route(
    '/category/<int:category_id>/item/<int:item_id>/edit',
    methods=['GET', 'POST'])
def editItem(category_id, item_id):

    if not hasAuthorization():
        return redirect(url_for('showLogin'))

    category = db_session.query(Category).filter_by(id=category_id).one()
    edit_item = db_session.query(Item).filter_by(id=item_id).one()

    # POST
    if request.method == 'POST':

        # Update item info
        edit_item.name = request.form['item']
        edit_item.description = request.form['description']
        edit_item.notes = request.form['notes']

        # Get image info
        image = request.files['photo']
        image_filename = None
        if image and allowed_file(image.filename):
            image_filename = secure_filename(image.filename)

        # Check and update image path
        if image_filename and image_filename != edit_item.image:

            # Delete old image from OS
            os.remove(os.path.join(
                app.config['UPLOAD_FOLDER'],
                edit_item.image))

            # Save new image to os
            edit_item.image = image_filename
            image.save(os.path.join(
                app.config['UPLOAD_FOLDER'],
                image_filename))

        # Update database
        db_session.add(edit_item)
        db_session.commit()

        flash('Item successfully edited')
        return redirect(url_for(
                            'showItem',
                            category_id=category_id,
                            item_id=item_id))
    # GET
    else:
        return render_template(
                        'editItem.html',
                        category=category,
                        item=edit_item,
                        login_session=login_session)


@app.route(
    '/category/<int:category_id>/item/<int:item_id>/delete',
    methods=['GET', 'POST'])
def deleteItem(category_id, item_id):

    if not hasAuthorization():
        return redirect(url_for('showLogin'))

    category = db_session.query(Category).filter_by(id=category_id).one()
    delete_item = db_session.query(Item).filter_by(id=item_id).one()

    # POST
    if request.method == 'POST':

        # Delete image from OS
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], delete_item.image))

        # Delete from database
        db_session.delete(delete_item)
        db_session.commit()

        flash('Item ' + delete_item.name + ' deleted')
        return redirect(url_for('showCategory', category_id=category_id))
    # GET
    else:
        return render_template(
                        'deleteItem.html',
                        category=category,
                        item=delete_item,
                        login_session=login_session)


@app.route(
    '/category/<int:category_id>/item/<int:item_id>/<int:comment_id>/delete',
    methods=['GET', 'POST'])
def deleteComment(category_id, item_id, comment_id):

    if not isUsersComment(comment_id=comment_id):
        return redirect(url_for('showLogin'))

    category = db_session.query(Category).filter_by(id=category_id).one()
    item = db_session.query(Item).filter_by(id=item_id).one()
    delete_comment = db_session.query(Comment).filter_by(id=comment_id).one()

    # POST
    if request.method == 'POST':
        db_session.delete(delete_comment)
        db_session.commit()
        flash('Comment deleted')
        return redirect(url_for(
                            'showItem',
                            category_id=category_id,
                            item_id=item_id))
    # GET
    else:
        return render_template(
            'deleteComment.html',
            category=category,
            item=item,
            comment=delete_comment,
            login_session=login_session)


@app.route(
    '/category/<int:category_id>/item/<int:item_id>/<int:comment_id>/edit',
    methods=['GET', 'POST'])
def editComment(category_id, item_id, comment_id):

    if not isUsersComment(comment_id=comment_id):
        return redirect(url_for('showLogin'))

    category = db_session.query(Category).filter_by(id=category_id).one()
    item = db_session.query(Item).filter_by(id=item_id).one()
    edit_comment = db_session.query(Comment).filter_by(id=comment_id).one()

    # POST
    if request.method == 'POST':
        edit_comment.text = request.form['comment']
        edit_comment.date = datetime.datetime.now()
        db_session.add(edit_comment)
        db_session.commit()
        flash('Comment edited')
        return redirect(url_for(
                    'showItem',
                    category_id=category_id,
                    item_id=item_id))
    # GET
    else:
        return render_template(
            'editComment.html',
            category=category,
            item=item,
            comment=edit_comment,
            login_session=login_session)


# Login routers
@app.route('/login')
def showLogin():

    # Create anti-forgery state token
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state

    # return "The current session state is %s" % login_session['state']
    return render_template(
                'login.html',
                STATE=state,
                login_session=login_session)


@csrf.exempt
@app.route('/fbconnect', methods=['POST'])
def fbconnect():

    # Object to old current FB API version
    fb_ver = 'v2.4'

    # Validate state token between server and client
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Obtain authorization code from client request
    access_token = request.data
    print "access token received %s" % access_token

    # Load Facebook client/app secret
    app_id = json.loads(
        open('/var/www/catalog/catalog/fb_client_secrets.json', 'r').read())['web']['app_id']
    app_secret = json.loads(
        open('/var/www/catalog/catalog/fb_client_secrets.json', 'r').read())['web']['app_secret']

    print "app id  %s" % app_id
    print "app secret %s" % app_secret

    # Set up URL with app secret and client access token
    url = "https://graph.facebook.com/oauth/access_token?" + \
        "grant_type=fb_exchange_token&client_id=%s&" % app_id + \
        "client_secret=%s" % app_secret + \
        "&fb_exchange_token=%s" % access_token

    # Obtain access token of the user via GET request
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Strip expire tag from access token
    token = result.split("&")[0]

    # Set up URL with user access token
    url = 'https://graph.facebook.com/%s/me?%s&fields=name,id,email' % \
        (fb_ver, token)

    # Obtain user info via GET request
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    print result
    print data

    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # Stored access token in the login_session to properly logout
    # Strip out the information before the equals sign in our token
    stored_token = token.split("=")[1]
    login_session['access_token'] = stored_token

    # Set up URL with access token
    url = 'https://graph.facebook.com/v2.4/me/picture?' + \
        '%s&redirect=0&height=200&width=200' % \
        token

    # Obtain user picture
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)

    # Store picturel URL
    login_session['picture'] = data["data"]["url"]

    # Get user id and store new user to database
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    # Generate HTML template to welcome login
    output = ''
    output += 'Welcome, '
    output += login_session['username']
    output += '!<br>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 100px;' + \
        'height: 100px;border-radius: 50px;' + \
        '-webkit-border-radius: 50px;-moz-border-radius: 50px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % \
        (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]

    del login_session['provider']
    del login_session['user_id']
    del login_session['username']
    del login_session['email']
    del login_session['picture']
    del login_session['facebook_id']

    flash("You've been logged out")
    return redirect(url_for('showCatalog'))


@app.route('/clearSession')
def clearSession():
    login_session.clear()
    flash("Your session has been cleared")
    categories = db_session.query(Category).order_by(Category.name).all()
    return render_template(
                'index.html',
                categories=categories,
                login_session=login_session)


# APIS
@app.route('/category/JSON')
def getCatalogJSON():
    catalog = db_session.query(Category).all()
    return jsonify(Categories=[c.serialize for c in catalog])


@app.route('/category/XML')
def getCatalogXML():
    catalog = db_session.query(Category).all()
    obj = {'Categories': [c.serialize for c in catalog]}
    return dicttoxml.dicttoxml(obj)


@app.route('/category/<int:category_id>/item/JSON')
def getItemsJSON(category_id):
    items = db_session.query(Item).filter_by(category_id=category_id).all()
    return jsonify(Items=[i.serialize for i in items])


@app.route('/category/<int:category_id>/item/XML')
def getItemsXML(category_id):
    items = db_session.query(Item).filter_by(category_id=category_id).all()
    obj = {'Items': [i.serialize for i in items]}
    return dicttoxml.dicttoxml(obj)


@app.route('/category/<int:category_id>/item/<int:item_id>/JSON')
def getItemDetailsJSON(category_id, item_id):
    item = db_session.query(Item).filter_by(id=item_id).one()
    return jsonify(Item=[item.serialize])


@app.route('/category/<int:category_id>/item/<int:item_id>/XML')
def getItemDetailsXML(category_id, item_id):
    item = db_session.query(Item).filter_by(id=item_id).one()
    obj = {'Item': [item.serialize]}
    return dicttoxml.dicttoxml(obj)

# Main (place at the end of the code)
if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
