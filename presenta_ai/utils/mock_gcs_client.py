import logging

class MockGCSClient:
    """
    A mock Google Cloud Storage client for local development and testing.
    Simulates file uploads and reads using an in-memory dictionary.
    """
    def __init__(self):
        self._storage = {}  # In-memory store: { "bucket_name/blob_name": "file_content_string" }
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def _get_full_path(self, blob_name: str, bucket_name: str) -> str:
        return f"{bucket_name}/{blob_name}"

    def upload_blob_from_string(self, blob_name: str, data_string: str, bucket_name: str = 'mock_bucket'):
        """
        Simulates uploading a string as a blob to a GCS bucket.

        Args:
            blob_name (str): The name of the blob (file path within the bucket).
            data_string (str): The string content of the file.
            bucket_name (str, optional): The name of the bucket. Defaults to 'mock_bucket'.
        """
        full_path = self._get_full_path(blob_name, bucket_name)
        self._storage[full_path] = data_string
        self.logger.info(f"MockGCS: Uploaded '{full_path}' ({len(data_string)} bytes)")

    def download_blob_to_string(self, blob_name: str, bucket_name: str = 'mock_bucket') -> str:
        """
        Simulates downloading a blob from GCS as a string.

        Args:
            blob_name (str): The name of the blob (file path within the bucket).
            bucket_name (str, optional): The name of the bucket. Defaults to 'mock_bucket'.

        Returns:
            str: The content of the blob as a string.

        Raises:
            FileNotFoundError: If the blob does not exist in the mock storage.
        """
        full_path = self._get_full_path(blob_name, bucket_name)
        if full_path not in self._storage:
            self.logger.error(f"MockGCS: File not found '{full_path}'")
            raise FileNotFoundError(f"MockGCS: Blob '{full_path}' not found in mock storage.")

        content = self._storage[full_path]
        self.logger.info(f"MockGCS: Downloaded '{full_path}' ({len(content)} bytes)")
        return content

    def blob(self, blob_name: str, bucket_name: str = 'mock_bucket'):
        """
        Returns a mock blob object.
        This is a simplified mock, actual GCS client blob objects have more methods.
        """
        # In a real GCS client, bucket.blob(blob_name) returns a Blob object.
        # We'll mock this by returning an object that has an `exists()` method.
        class MockBlob:
            def __init__(self, client, full_path, blob_name, bucket_name):
                self._client = client
                self._full_path = full_path
                self.name = blob_name
                self.bucket = bucket_name # Mock bucket attribute

            def exists(self):
                return self._full_path in self._client._storage

            def upload_from_string(self, data_string: str):
                self._client.upload_blob_from_string(self.name, data_string, self.bucket)

            def download_as_string(self) -> bytes:
                # GCS download_as_string returns bytes, so we encode our string
                return self._client.download_blob_to_string(self.name, self.bucket).encode('utf-8')

        full_path = self._get_full_path(blob_name, bucket_name)
        return MockBlob(self, full_path, blob_name, bucket_name)

    def bucket(self, bucket_name: str):
        """
        Returns a mock bucket object.
        This is a simplified mock.
        """
        # In a real GCS client, client.bucket(bucket_name) returns a Bucket object.
        # We'll mock this by returning an object that has a `blob()` method.
        class MockBucket:
            def __init__(self, client, name):
                self._client = client
                self.name = name

            def blob(self, blob_name: str):
                return self._client.blob(blob_name, self.name)

        return MockBucket(self, bucket_name)

if __name__ == '__main__':
    # Example Usage
    mock_client = MockGCSClient()

    # Simulate upload
    file_content = "This is a test presentation file."
    file_gcs_path = "presentations/test_presentation.txt"
    mock_client.upload_blob_from_string(file_gcs_path, file_content)

    # Simulate download
    try:
        retrieved_content = mock_client.download_blob_to_string(file_gcs_path)
        assert retrieved_content == file_content
        logging.info(f"Successfully retrieved: {retrieved_content}")
    except FileNotFoundError as e:
        logging.error(e)

    # Simulate checking if blob exists
    bucket_obj = mock_client.bucket('mock_bucket')
    blob_obj = bucket_obj.blob(file_gcs_path)
    logging.info(f"Blob '{file_gcs_path}' exists: {blob_obj.exists()}")

    non_existent_blob = bucket_obj.blob("non_existent.txt")
    logging.info(f"Blob 'non_existent.txt' exists: {non_existent_blob.exists()}")

    # Simulate upload and download using blob object methods
    file_content_v2 = "Another test file via blob object."
    file_gcs_path_v2 = "presentations/test_presentation_v2.txt"
    blob_v2 = mock_client.bucket('mock_bucket').blob(file_gcs_path_v2)
    blob_v2.upload_from_string(file_content_v2)
    retrieved_content_v2_bytes = blob_v2.download_as_string()
    retrieved_content_v2 = retrieved_content_v2_bytes.decode('utf-8')
    assert retrieved_content_v2 == file_content_v2
    logging.info(f"Successfully retrieved via blob object: {retrieved_content_v2}")
