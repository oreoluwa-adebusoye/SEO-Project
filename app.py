from flask import Flask, render_template, url_for, flash, redirect
from forms import RegistrationForm, ProfileForm
from flask import request

app = Flask(__name__)
app.config['SECRET_KEY'] = '31cf3dbee0da6ac8e22e3a06e26263b7q'  

@app.route("/")
def home():
    return render_template("home.html")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = RegistrationForm()
    if form.validate_on_submit():
        flash("Signup successful!", "success")
        #return redirect(url_for('home'))  # Redirect later to home or dashboard
        return redirect(url_for('create_profile')) # now redirect to create profile page

    return render_template('signup.html', form=form)

@app.route('/create_profile', methods=['GET', 'POST'])
def create_profile():
    form = ProfileForm()
    if form.validate_on_submit():
        flash("Profile created successfully!", "success")
        return redirect(url_for('home'))
    return render_template('create_profile.html', form=form)

@app.route("/homepage")
def homepage():
    return render_template("homepage.html")  

@app.route("/events")
def events():
    return render_template("events.html")  

@app.route("/user_profile")
def user_profile():
    return render_template("user_profile_page.html")

if __name__ == "__main__":
    app.run(debug=True)
