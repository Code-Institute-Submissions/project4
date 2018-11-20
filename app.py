from flask import Flask, render_template, request, redirect, session
import os
from flask_pymongo import PyMongo

import time
from bson.objectid import ObjectId
import json
from flask_mongo_sessions import MongoDBSessionInterface
from werkzeug.security import generate_password_hash, \
     check_password_hash



app = Flask(__name__)

app.config['MONGO_DBNAME'] = "cookbook"
app.config['MONGO_URI'] = "mongodb://admin:verysecret12@ds241012.mlab.com:41012/cookbook"


mongo = PyMongo(app)



with app.app_context():
    app.session_interface = MongoDBSessionInterface(app, mongo.db, 'sessions')



@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect('login')
    


@app.route('/login', methods=['POST', 'GET'])
def login():
    if 'user' in session:
        return render_template('login.html', msg = "Already logged in", user = session['user'])

    if request.method == 'POST':
        user = mongo.db.users.find_one({ "name": request.form['user'] })
        if user:
            if check_password_hash(user['password'], request.form['password']):
                session['user'] = user['name']
                return render_template('login.html', user = session['user'], msg = "Login successful")
        
    return render_template('login.html')
    
@app.route('/register', methods = ['POST', 'GET'])
def register():
    if request.method == 'POST':
        user = mongo.db.users.find_one({ "name": request.form['user'] })
        if user:
            return render_template('register.html', form = request.form) # send the form back so we can prefill the inputs for another attempt.
        else:
            mongo.db.users.insert_one( { "name" : request.form['user'], "email" : request.form['email'], "password" : generate_password_hash(request.form['password'])})
            return render_template('register.html', success = True )
    
    return render_template('register.html')
        
@app.route('/')
@app.route('/deleted')
@app.route('/edited')
def index():
    return render_template('index.html', recipies = mongo.db.recipies.find())
    
    
@app.route('/sort/<sort_by>/<ad>')
def index_sorted(sort_by, ad):
    if ad == 'asc':
        direction = 1
    else:
        direction = -1

    return render_template('index.html', sort = "{} ({})".format(sort_by, ad), recipies = mongo.db.recipies.find().sort([ (sort_by, direction) ]))
    
@app.route('/add_recipe')
def add_recipe():
    return render_template('add_recipe.html', categories = mongo.db.categories.find())

@app.route('/insert_recipe', methods= ['POST'])
def insert_recipe():
    
    
    tmp_dict = {}
    tmp = request.form.to_dict()

    tmp['ingredients'] =  tmp['ingredients'].replace('\r\n', ',')
    
    
    #if tmp['ingredients'][-1:] == ',':
    #    tmp['ingredients'] =  tmp['ingredients'][:-1]
        

    # string.split() creates a list
    l_one = tmp['ingredients'].split(',')

    for i in range(0, len(l_one), 1):
        l_two = l_one[i].split('-')
        if len(l_two) == 2: # if the list isnt complete with key - value pair it means it's likely a comma from leading or trailing \r\n
            tmp_dict[l_two[0]] = l_two[1]
    

    tmp['ingredients'] = tmp_dict
    
    # Much easier to store it here than use mongodb's aggregate() later
    tmp['ingredients_count'] = len(tmp_dict)
    
    # remove keys we won't be using

    del tmp['action']
    
    # last we need to add keys for date and upvotes
    
    tmp['date_added'] = time.ctime();
    tmp['upvotes'] = 0
    
    mongo.db.recipies.insert_one(tmp)
    return redirect('/')
    
    # 
    # return render_template('index.html', dic = tmp)
    
    
    
@app.route('/details/<recipe_id>')
def recipe_details(recipe_id):
    
    return render_template('recipe_details.html', recipe = mongo.db.recipies.find_one({ '_id': ObjectId(recipe_id) }))

@app.route('/edit/<recipe_id>')
def edit_recipe(recipe_id):
    recipe = mongo.db.recipies.find_one({'_id': ObjectId(recipe_id) })
    ingredients = recipe['ingredients']
    return render_template('edit_recipe.html',categories = mongo.db.categories.find(), recipe = recipe, ingredients = ingredients )

@app.route('/delete/<recipe_id>')
def delete_recipe(recipe_id):
    mongo.db.recipies.delete_one({'_id': ObjectId(recipe_id) })
    return redirect('/deleted')
    
@app.route('/action/<recipe_id>', methods=["POST"])
def decide_action(recipe_id):
    if 'edit_button' in request.form.to_dict():
        return edit_recipe(recipe_id)
    else:
        return delete_recipe(recipe_id)

    return redirect('/')
    
@app.route('/update/<recipe_id>', methods=["POST"])
def update_recipe(recipe_id):
    # apparently not really an update, but same experience for the user and less code and more elegant I think.
   insert_recipe()
   mongo.db.recipies.delete_one({'_id': ObjectId(recipe_id) })
   return redirect('/')


# This is AJAX only
@app.route('/upvote/<recipe_id>', methods=["POST"])
def upvote_recipe(recipe_id):

    mongo.db.recipies.update({ '_id': ObjectId(recipe_id) }, { '$inc': { 'upvotes': 1 }})
    return "OK"


if __name__ == '__main__':
    app.run(host = os.getenv('IP', '0.0.0.0'),
            port = os.getenv('PORT', '8080'),
            debug = True
            )