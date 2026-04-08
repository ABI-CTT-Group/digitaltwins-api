from pathlib import Path
from digitaltwins.core.uploader import Uploader

if __name__ == "__main__":
    script_dir = Path(__file__).resolve().parent
    datasets_dir = script_dir / "data/example_sds_dataset"

    uploader = Uploader()
    dataset_uuid = uploader.upload_dataset(
        dataset_path=str(datasets_dir),
        category="measurement",
        save_json=False,
    )
    print(f"Dataset UUID: {dataset_uuid}")
