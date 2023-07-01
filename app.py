from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jobs.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Jobs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_type = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    client_id = db.Column(db.String(200), nullable=False)
    employee_id_1 = db.Column(db.String(200), nullable=True)
    employee_id_2 = db.Column(db.String(200), nullable=True)


@app.route('/', methods=['GET', 'POST'])

def start_page():
    if request.method == 'POST':
        if request.form['action'] == 'update':
            new_job = Jobs(
                task_type = request.form['task_type'],
                quantity = request.form['quantity'],
                client_id = request.form['client_id']
            )
            db.session.add(new_job)
            db.session.commit()
    if request.method == 'POST':
        if request.form['action'] == 'delete':
            Jobs.query.filter(Jobs.id == request.form['id']).delete()
            db.session.commit()

    all_jobs = Jobs.query.order_by(Jobs.date_created).all()

    return render_template('index.html', all_jobs=all_jobs)

if __name__ == '__main__':
    app.run(debug=True)