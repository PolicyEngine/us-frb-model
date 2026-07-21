from scripts.check_artifact_manifest import verify_manifest


def test_model_and_data_artifacts_have_independent_verified_hashes():
    observed = verify_manifest()
    assert set(observed) == {"model_package", "model_xml", "data_package", "longbase"}
    assert observed["model_package"] != observed["data_package"]
