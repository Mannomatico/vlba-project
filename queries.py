dataset_id = "vlba-maintenance-and-service.MwwMs_Data"

QUERIES = {
    "get_all_clients": f"SELECT ClientId, ClientName, CONCAT(PostalCode, ',', City, ',DE') as Location \
                        FROM `{dataset_id}.Clients` \
                        ORDER BY ClientId ASC",

    "predict_best_team": f'WITH predictions AS ( \
                        SELECT predicted_TotalWorkingHours, TeamId \
                        FROM ML.PREDICT(MODEL `vlba-maintenance-and-service.MwwMs_Data.model1`, \
                        (SELECT \
                        "Electronics repair" as TaskType, \
                        TeamId, \
                        ClientId, \
                        ClientName, \
                        DistanceSP1ToClient, \
                        Quantity, \
                        ServiceTaskId \
                        FROM ( \
                        SELECT DISTINCT \
                        "Electronics repair" as TaskType, \
                        TeamId, \
                        ClientId, \
                        ClientName, \
                        DistanceSP1ToClient, \
                        Quantity, \
                        ServiceTaskId \
                        FROM `vlba-maintenance-and-service.MwwMs_Data.Team_Facts` \
                        ) \
                        )) \
                        ) \
                        SELECT p.predicted_TotalWorkingHours, p.TeamId \
                        FROM predictions p \
                        JOIN ( \
                        SELECT MIN(predicted_TotalWorkingHours) AS min_predicted_TotalWorkingHours \
                        FROM predictions \
                        ) m \
                        ON p.predicted_TotalWorkingHours = m.min_predicted_TotalWorkingHours'
}
