"""
IBM Cloudant Uploader Utility

This module provides functionality to upload NYC rental listing data
from JSON files to an IBM Cloudant database.

Usage as a script:
    python utilities/cloudant_uploader.py data/nyc_both_20260131_161453.json

Usage as a module:
    from utilities import CloudantUploader
    uploader = CloudantUploader()
    uploader.upload_from_json('data/nyc_both_20260131_161453.json')
"""

import json
import os
import sys
from typing import Dict, List, Any, Optional
from pathlib import Path

from ibmcloudant.cloudant_v1 import CloudantV1, Document
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_cloud_sdk_core import ApiException
from dotenv import load_dotenv


class CloudantUploader:
    """
    Handles uploading rental listing data to IBM Cloudant database.

    Attributes:
        client: IBM Cloudant V1 client instance
        db_name: Name of the Cloudant database to use
    """

    def __init__(
        self,
        url: Optional[str] = None,
        apikey: Optional[str] = None,
        db_name: Optional[str] = None,
    ):
        """
        Initialize the Cloudant uploader.

        Args:
            url: IBM Cloudant service URL (defaults to CLOUDANT_URL env var)
            apikey: IBM Cloudant API key (defaults to CLOUDANT_APIKEY env var)
            db_name: Database name (defaults to CLOUDANT_DB_NAME env var)

        Raises:
            ValueError: If required credentials are not provided
        """
        # Load environment variables from .env file if it exists
        load_dotenv()

        # Get credentials from parameters or environment variables
        self.url = url or os.getenv("CLOUDANT_URL")
        self.apikey = apikey or os.getenv("CLOUDANT_APIKEY")
        self.db_name = db_name or os.getenv("CLOUDANT_DB_NAME", "nyc_rentals")

        # Validate required credentials
        if not self.url or not self.apikey:
            raise ValueError(
                "Cloudant credentials are required. Please provide:\n"
                "  - CLOUDANT_URL\n"
                "  - CLOUDANT_APIKEY\n"
                "Either as parameters or environment variables."
            )

        # Initialize Cloudant client
        self.client = self._initialize_client()
        print(f"✓ Connected to IBM Cloudant")

    def _initialize_client(self) -> CloudantV1:
        """
        Initialize and authenticate IBM Cloudant client.

        Returns:
            Authenticated CloudantV1 client instance
        """
        authenticator = IAMAuthenticator(self.apikey)
        client = CloudantV1(authenticator=authenticator)
        client.set_service_url(self.url)
        return client

    def create_database_if_not_exists(self) -> bool:
        """
        Create the database if it doesn't already exist.

        Returns:
            True if database was created, False if it already exists
        """
        try:
            self.client.put_database(db=self.db_name).get_result()
            print(f"✓ Created database: {self.db_name}")
            return True
        except ApiException as e:
            if e.code == 412:  # Database already exists
                print(f"✓ Database already exists: {self.db_name}")
                return False
            else:
                raise

    def transform_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a document for Cloudant storage.

        Converts "N/A" strings to null values for better querying.
        Cloudant will auto-generate _id field.

        Args:
            doc: Original document dictionary

        Returns:
            Transformed document dictionary
        """
        transformed = {}
        for key, value in doc.items():
            # Convert "N/A" strings to None (which becomes null in JSON)
            if value == "N/A":
                transformed[key] = None
            else:
                transformed[key] = value

        return transformed

    def load_json_file(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Load and parse JSON file containing rental listings.

        Args:
            file_path: Path to the JSON file

        Returns:
            List of document dictionaries

        Raises:
            FileNotFoundError: If the file doesn't exist
            json.JSONDecodeError: If the file is not valid JSON
        """
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            raise FileNotFoundError(f"JSON file not found: {file_path}")

        with open(file_path_obj, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("JSON file must contain an array of documents")

        print(f"✓ Loaded {len(data)} documents from {file_path_obj.name}")
        return data

    def bulk_upload(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Upload documents to Cloudant in bulk.

        Args:
            documents: List of document dictionaries to upload

        Returns:
            Dictionary with upload statistics (total, successful, failed)
        """
        if not documents:
            print("⚠ No documents to upload")
            return {"total": 0, "successful": 0, "failed": 0}

        # Transform documents (convert N/A to null)
        transformed_docs = [self.transform_document(doc) for doc in documents]

        # Convert to Document objects
        doc_objects = [Document(**doc) for doc in transformed_docs]

        print(
            f"⏳ Uploading {len(doc_objects)} documents to database '{self.db_name}'..."
        )

        try:
            # Bulk insert documents
            result = self.client.post_bulk_docs(
                db=self.db_name, bulk_docs={"docs": doc_objects}
            ).get_result()

            # Count successes and failures
            successful = 0
            failed = 0
            failed_docs = []

            for idx, doc_result in enumerate(result):
                if "error" in doc_result:
                    failed += 1
                    failed_docs.append(
                        {
                            "index": idx,
                            "error": doc_result.get("error"),
                            "reason": doc_result.get("reason"),
                        }
                    )
                else:
                    successful += 1

            # Print results
            print(f"✓ Upload complete!")
            print(f"  Total: {len(documents)}")
            print(f"  Successful: {successful}")
            print(f"  Failed: {failed}")

            if failed_docs:
                print(f"\n⚠ Failed documents:")
                for fail in failed_docs[:5]:  # Show first 5 failures
                    print(
                        f"  - Index {fail['index']}: {fail['error']} - {fail['reason']}"
                    )
                if len(failed_docs) > 5:
                    print(f"  ... and {len(failed_docs) - 5} more")

            return {
                "total": len(documents),
                "successful": successful,
                "failed": failed,
                "failed_docs": failed_docs,
            }

        except ApiException as e:
            print(f"✗ Error uploading documents: {e.message}")
            raise

    def upload_from_json(self, json_file_path: str) -> Dict[str, Any]:
        """
        Complete workflow: Load JSON file and upload to Cloudant.

        Args:
            json_file_path: Path to the JSON file containing rental listings

        Returns:
            Dictionary with upload statistics
        """
        # Ensure database exists
        self.create_database_if_not_exists()

        # Load documents from JSON file
        documents = self.load_json_file(json_file_path)

        # Upload to Cloudant
        result = self.bulk_upload(documents)

        return result


def main():
    """
    Command-line interface for the Cloudant uploader.
    """
    if len(sys.argv) < 2:
        print("Usage: python utilities/cloudant_uploader.py <json_file_path>")
        print("\nExample:")
        print(
            "  python utilities/cloudant_uploader.py data/nyc_both_20260131_161453.json"
        )
        print("\nRequired environment variables:")
        print("  CLOUDANT_URL - IBM Cloudant service URL")
        print("  CLOUDANT_APIKEY - IBM Cloudant API key")
        print(
            "  CLOUDANT_DB_NAME - Database name (optional, defaults to 'nyc_rentals')"
        )
        sys.exit(1)

    json_file = sys.argv[1]

    try:
        uploader = CloudantUploader()
        result = uploader.upload_from_json(json_file)

        if result["failed"] > 0:
            sys.exit(1)

    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
