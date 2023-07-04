from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from google.cloud import bigquery
from google.oauth2 import service_account
from datetime import datetime
from queries import QUERIES
import json

app = Flask(__name__)

# SQLite DB Connection
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///jobs.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# BigQuery Connection
dataset_id = "vlba-maintenance-and-service.MwwMs_Data"
credentials = service_account.Credentials.from_service_account_file("credentials.json")
client = bigquery.Client(credentials=credentials)

# maps api key
with open('maps_key.json', 'r') as f:
  data = json.load(f)
maps_key = data['maps_key']

class Jobs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.String(200), nullable=True)
    task_type = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    client_id = db.Column(db.String(200), nullable=False)
    client_name = db.Column(db.String(200), nullable=False)
    team_members = db.Column(db.String(200), nullable=True)
    total_working_hours = db.Column(db.Double, nullable=True)
    distance = db.Column(db.Double, nullable=True)


@app.route("/", methods=["GET", "POST"])
def start_page():
    # job creation
    if request.method == "POST":
        if request.form["action"] == "update":
            if(request.form["quantity"].isnumeric()):
                best_team = predict_best_team(request.form["task_type"], get_client_id(request.form["client_name"]), request.form["quantity"])
                workers = get_team_members(best_team['team_id'])

                new_job = Jobs(
                    task_type=request.form["task_type"],
                    quantity=request.form["quantity"],
                    client_name=request.form["client_name"],
                    client_id=get_client_id(request.form["client_name"]),
                    total_working_hours= "%.2f" % best_team["working_time"],
                    team_id=best_team["team_id"],
                    team_members=workers
                )
                db.session.add(new_job)
                db.session.commit()

    # job deletion
    if request.method == "POST":
        if request.form["action"] == "delete":
            Jobs.query.filter(Jobs.id == request.form["id"]).delete()
            db.session.commit()

    # render map
    if request.method == "POST":
        if request.form["action"] == "map":
            return render_template(
                "map.html", location=get_location(request.form["client_id"]), maps_key = maps_key
            )

    # get all active jobs
    all_jobs = Jobs.query.order_by(Jobs.date_created).all()

    # get all client_ids
    all_clients = get_all_clients()
    all_client_names = sorted([d['client_name'] for d in all_clients])

    # return page
    return render_template("index.html", all_jobs=all_jobs, all_client_names = all_client_names)


# get a list of clients
def get_all_clients():
    table = client.query(QUERIES["get_all_clients"]).result()
   
    clients = []

    for row in table:
        clients.append(
            {
                "client_id": row.ClientId,
                "client_name": row.ClientName,
                "location": row.Location,
            }
        )

    return clients


# returns a location of a client_id in Format: 'POSTCODE,CITY,DE'
def get_location(client_id):
    clients = get_all_clients()
    return next(item for item in clients if item["client_id"] == client_id)["location"]


# returns the best team and expected total working hours of a specific task, client_id and quantity
def predict_best_team(task_type, client_id, quantity):
    table = client.query(QUERIES["predict_best_team"]).result()
    best_teams = []
    if((task_type == 'Bike repair') | (task_type == 'Electronics repair') | (task_type == 'Engine check')):
        table = client.query(f'WITH predictions AS ( \
                              SELECT \
                                predicted_TotalWorkingHours, \
                                TeamId, \
                                ClientId, \
                                TaskType \
                              FROM ML.PREDICT(MODEL `vlba-maintenance-and-service.MwwMs_Data.Facts_Model1`, \
                                ( \
                                SELECT \
                                  ClientId, \
                                  Quantity, \
                                  TaskTeamWorkingExperience, \
                                  TaskType, \
                                 TeamId \
                               FROM ( \
                                 SELECT DISTINCT \
                                   ClientId, \
                                   Quantity, \
                                   TaskTeamWorkingExperience, \
                                    TaskType, \
                                    TeamId \
                                  FROM `vlba-maintenance-and-service.MwwMs_Data.Team_Facts_Model1` \
                                ) \
                              )) \
                            ) \
                            SELECT \
                              p.ClientId, \
                              p.TeamId, \
                              p.TaskType, \
                              AVG(p.predicted_TotalWorkingHours) AS mean_predicted_TotalWorkingHours \
                            FROM \
                              predictions p \
                            WHERE \
                              p.ClientId = "{client_id}" AND \
                              p.TaskType = "{task_type}" \
                            GROUP BY \
                              p.ClientId, \
                              p.TeamId, \
                              p.TaskType \
                            ORDER BY mean_predicted_TotalWorkingHours').result()

        for row in table:
            best_teams.append(
                {
                    "working_time": row.mean_predicted_TotalWorkingHours,
                    "team_id": row.TeamId
                }
            )
    else:
        table = client.query(f'WITH predictions AS ( \
                              SELECT \
                                predicted_TotalWorkingHours, \
                                TeamId, \
                                ClientId, \
                                TaskType \
                              FROM ML.PREDICT(MODEL `vlba-maintenance-and-service.MwwMs_Data.Facts_Model2`, \
                                ( \
                                SELECT \
                                  ClientId, \
                                  Quantity, \
                                  TaskTeamWorkingExperience, \
                                  TaskType, \
                                 TeamId \
                               FROM ( \
                                 SELECT DISTINCT \
                                   ClientId, \
                                   Quantity, \
                                   TaskTeamWorkingExperience, \
                                    TaskType, \
                                    TeamId \
                                  FROM `vlba-maintenance-and-service.MwwMs_Data.Team_Facts_Model2` \
                                ) \
                              )) \
                            ) \
                            SELECT \
                              p.ClientId, \
                              p.TeamId, \
                              p.TaskType, \
                              AVG(p.predicted_TotalWorkingHours) AS mean_predicted_TotalWorkingHours \
                            FROM \
                              predictions p \
                            WHERE \
                              p.ClientId = "{client_id}" AND \
                              p.TaskType = "{task_type}" \
                            GROUP BY \
                              p.ClientId, \
                              p.TeamId, \
                              p.TaskType \
                            ORDER BY mean_predicted_TotalWorkingHours').result()

        for row in table:
            best_teams.append(
                {
                    "working_time": row.mean_predicted_TotalWorkingHours,
                    "team_id": row.TeamId
                }
            )

    not_available_teams = []
    all_jobs = Jobs.query.order_by(Jobs.date_created).all()

    for job in all_jobs:
        not_available_teams.append(job.team_members)

    for team in best_teams:
        team_employees = get_team_members_as_list(team['team_id'])
        team_available = True
        for employee in team_employees:
            for team2 in not_available_teams:
                if employee in team2:
                    team_available = False
        if team_available:
            team['working_time'] = team['working_time']*float(quantity)
            return team
        
    return(
        {
            "working_time": 0,
            "team_id": 0
        }
    )


# returns the team members of a team_id as string
def get_team_members(team_id):
    team_data = get_team_members_as_list(team_id)

    if len(team_data) == 0:
        return ""
    elif len(team_data) == 1:
        return team_data[0]
    else:
        return team_data[0] + ", " + team_data[1]


# returns the team members of a team_id as string
def get_team_members_as_list(team_id):
    table = client.query(f"SELECT DISTINCT ServiceEmployeeId \
                        FROM `{dataset_id}.Team_Facts` AS a \
                        INNER JOIN `{dataset_id}.Assigned_Employess_Task` AS b \
                        ON a.ServiceTaskId = b.ServiceTaskId \
                        WHERE TeamId={team_id}").result()
    
    team_data = []

    for row in table:
        team_data.append(row.ServiceEmployeeId)

    return team_data


# returns client name from client_id
def get_client_id(client_name):
    clients = get_all_clients()
    client_id = ""
    for i in clients:
        if i["client_name"] == client_name:
            client_id = i["client_id"]
    return client_id


if __name__ == "__main__":
    app.run(debug=True)
