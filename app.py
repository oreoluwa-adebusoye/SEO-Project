from flask import Flask, render_template, url_for, flash, redirect
from forms import RegistrationForm

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
        return redirect(url_for('home'))  # Redirect later to home or dashboard
    return render_template('signup.html', form=form)

if __name__ == "__main__":
    app.run(debug=True)
