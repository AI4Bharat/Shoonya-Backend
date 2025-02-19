def get_batch_dataset_upload_status(instance_ids):
    """
    Batch fetch upload status for a list of dataset instance IDs.
    Replace this with actual logic to retrieve status from your database.
    """
    # Mock data for testing
    status_data = {}
    for instance_id in instance_ids:
        status_data[instance_id] = {
            "last_upload_status": "Completed",
            "last_upload_date": "2023-01-01",
            "last_upload_time": "12:00:00",
            "last_upload_result": "Success",
        }
    return status_data