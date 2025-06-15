"""
Mock Google Cloud Storage (GCS) client for local development and testing.

This module provides a `MockGCSClient` class that simulates basic GCS
operations like uploading and downloading blobs (as strings) using an
in-memory dictionary as storage. It also provides mock `Bucket` and `Blob`
objects with a limited set of methods (`exists`, `upload_from_string`,
`download_as_string`) to mimic the behavior of the actual Google Cloud
Storage client library.

This is useful for testing application logic that interacts with GCS without
requiring actual GCS access or credentials, especially in automated tests
or local UI development.
"""
import logging

# Configure logger for this module
logger = logging.getLogger(__name__)

class MockGCSClient:
    """
    A mock Google Cloud Storage client for local development and testing.

    Simulates file uploads and reads using an in-memory dictionary. This client
    primarily works with string data for simplicity, which is suitable for
    applications where file content is treated as text or can be represented
    as such for mocking purposes (e.g., mock presentation content).
    """
    def __init__(self):
        """Initializes the MockGCSClient with an empty in-memory storage."""
        self._storage: Dict[str, str] = {}  # In-memory store: { "bucket_name/blob_name": "file_content_string" }
        # BasicConfig is called here to ensure logs are visible if this client is used standalone
        # or before application-wide logging is configured. It's safe if already configured.
        if not logging.getLogger().hasHandlers(): # Check if root logger has handlers
            logging.basicConfig(level=logging.INFO)
        # self.logger = logging.getLogger(__name__) # Using module-level logger

    def _get_full_path(self, blob_name: str, bucket_name: str) -> str:
        """Constructs the full path key used for in-memory storage."""
        return f"{bucket_name}/{blob_name}"

    def upload_blob_from_string(self, blob_name: str, data_string: str, bucket_name: str = 'mock_bucket'):
        """
        Simulates uploading a string as a blob to a GCS bucket.

        The data is stored in an in-memory dictionary.

        Args:
            blob_name (str): The name of the blob (simulating file path within the bucket).
            data_string (str): The string content of the "file".
            bucket_name (str, optional): The name of the bucket. Defaults to 'mock_bucket'.
        """
        full_path = self._get_full_path(blob_name, bucket_name)
        self._storage[full_path] = data_string
        logger.info(f"MockGCS: Uploaded '{full_path}' ({len(data_string)} bytes)")

    def download_blob_to_string(self, blob_name: str, bucket_name: str = 'mock_bucket') -> str:
        """
        Simulates downloading a blob from GCS as a string.

        Retrieves data from the in-memory storage.

        Args:
            blob_name (str): The name of the blob.
            bucket_name (str, optional): The name of the bucket. Defaults to 'mock_bucket'.

        Returns:
            str: The content of the blob as a string.

        Raises:
            FileNotFoundError: If the blob does not exist in the mock storage.
        """
        full_path = self._get_full_path(blob_name, bucket_name)
        if full_path not in self._storage:
            logger.error(f"MockGCS: File not found '{full_path}'")
            raise FileNotFoundError(f"MockGCS: Blob '{full_path}' not found in mock storage.")

        content = self._storage[full_path]
        logger.info(f"MockGCS: Downloaded '{full_path}' ({len(content)} bytes)")
        return content

    def blob(self, blob_name: str, bucket_name: str = 'mock_bucket') -> 'MockBlob':
        """
        Returns a mock Blob object.

        This is a simplified mock. Real GCS client Blob objects have many more methods.
        This mock provides `exists()`, `upload_from_string()`, and `download_as_string()`.

        Args:
            blob_name (str): The name of the blob.
            bucket_name (str, optional): The name of the bucket. Defaults to 'mock_bucket'.

        Returns:
            MockBlob: A mock Blob object associated with this client.
        """
        full_path = self._get_full_path(blob_name, bucket_name)
        return MockBlob(self, full_path, blob_name, bucket_name)

    def bucket(self, bucket_name: str) -> 'MockBucket':
        """
        Returns a mock Bucket object.

        This is a simplified mock. Real GCS client Bucket objects have more methods.
        This mock mainly provides a `blob()` method to get a MockBlob object.

        Args:
            bucket_name (str): The name of the bucket.

        Returns:
            MockBucket: A mock Bucket object associated with this client.
        """
        return MockBucket(self, bucket_name)

class MockBlob:
    """
    A mock GCS Blob object, providing a subset of `google.cloud.storage.Blob` methods.
    """
    def __init__(self, client: MockGCSClient, full_path: str, blob_name: str, bucket_name: str):
        """
        Initializes a MockBlob.

        Args:
            client (MockGCSClient): The mock client instance.
            full_path (str): The full path used as a key in the client's storage.
            blob_name (str): The name of this blob.
            bucket_name (str): The name of the bucket this blob belongs to.
        """
        self._client = client
        self._full_path = full_path
        self.name = blob_name
        self.bucket_name = bucket_name # Changed from self.bucket to self.bucket_name for clarity

    def exists(self) -> bool:
        """Checks if the blob exists in the mock client's storage."""
        return self._full_path in self._client._storage

    def upload_from_string(self, data_string: str):
        """Simulates uploading string data to this blob."""
        self._client.upload_blob_from_string(self.name, data_string, self.bucket_name)

    def download_as_string(self) -> bytes:
        """
        Simulates downloading the blob's content as a UTF-8 encoded byte string.
        Note: The actual GCS library method is `download_as_bytes()`.
        This mock keeps `download_as_string` for consistency with its string-based storage
        but returns bytes as the real API often does for this method name.
        """
        content_str = self._client.download_blob_to_string(self.name, self.bucket_name)
        return content_str.encode('utf-8')

class MockBucket:
    """
    A mock GCS Bucket object, providing a `blob()` method.
    """
    def __init__(self, client: MockGCSClient, name: str):
        """
        Initializes a MockBucket.

        Args:
            client (MockGCSClient): The mock client instance.
            name (str): The name of this bucket.
        """
        self._client = client
        self.name = name

    def blob(self, blob_name: str) -> MockBlob:
        """
        Gets a MockBlob object for a blob within this bucket.

        Args:
            blob_name (str): The name of the blob.

        Returns:
            MockBlob: The MockBlob object.
        """
        return self._client.blob(blob_name, self.name)


if __name__ == '__main__':
    # Ensure basic logging is configured if running standalone for testing
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=logging.INFO)
    logger_main = logging.getLogger(__name__) # Use a specific logger for __main__

    logger_main.info("--- Testing MockGCSClient ---")
    mock_client = MockGCSClient()

    # Test direct upload and download
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
