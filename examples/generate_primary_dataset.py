"""
Example for generating a SDS primary dataset
"""
import os.path

from sparc_me import Dataset


def add_dataset_description(dataset, save_dir):
    """
    the values can be filled in by 2 methods, set_field() or set_field_using_row_name().

    This example will use Dataset.set_field()
    # You can get the row_index by looking at
    #   1. the saved metadata file dataset_description.xlsx. Excel index starts from 1 where index 1 is the header row. so actual data index starts from 2.
    #   2. or the DataFrame object in the python code. dataset._dataset.dataset_description.metadata
    """

    dataset.set_field(category="dataset_description", row_index=2, header="Value", value="2.0.0")
    dataset.set_field(category="dataset_description", row_index=3, header="Value", value="experimental")
    dataset.set_field(category="dataset_description", row_index=5, header="Value",
                      value="Dynamic contrast-enhanced magnetic resonance images of breast cancer patients with tumor locations (Duke-Breast-Cancer-MRI)")
    dataset.set_field(category="dataset_description", row_index=6, header="Value", value="""Background Recent studies showed preliminary data on associations of MRI-based imaging phenotypes of breast tumours with breast cancer molecular, genomic, and related characteristics. In this study, we present a comprehensive analysis of this relationship.
    Methods We analysed a set of 922 patients with invasive breast cancer and pre-operative MRI. The MRIs were analysed by a computer algorithm to extract 529 features of the tumour and the surrounding tissue. Machine-learning-based models based on the imaging features were trained using a portion of the data (461 patients) to predict the following molecular, genomic, and proliferation characteristics: tumour surrogate molecular subtype, oestrogen receptor, progesterone receptor and human epidermal growth factor status, as well as a tumour proliferation marker (Ki-67). Trained models were evaluated on the set of the remaining 461 patients.
    Results Multivariate models were predictive of Luminal A subtype with AUC = 0.697 (95% CI: 0.647–0.746, p < .0001), triple negative breast cancer with AUC = 0.654 (95% CI: 0.589–0.727, p < .0001), ER status with AUC = 0.649 (95% CI: 0.591–0.705, p < .001), and PR status with AUC = 0.622 (95% CI: 0.569–0.674, p < .0001). Associations between individual features and subtypes we also found.
    Conclusions There is a moderate association between tumour molecular biomarkers and algorithmically assessed imaging features.""")
    dataset.set_field(category="dataset_description", row_index=7, header="Value", value="Breast cancer")
    dataset.set_field(category="dataset_description", row_index=7, header="Value 2", value="MRI")
    dataset.set_field(category="dataset_description", row_index=11, header="Value",
                      value="""Breast MRI is a common image modality to assess the extent of disease in breast cancer patients. Recent studies show that MRI has a potential in prognosis of patients’ short and long-term outcomes as well as predicting pathological and genomic features of the tumors. However, large, well annotated datasets are needed to make further progress in the field. We share such a dataset here.""")
    dataset.set_field(category="dataset_description", row_index=12, header="Value", value="""In terms of design, the dataset is a single-institutional, retrospective collection of 922 biopsy-confirmed invasive breast cancer patients, over a decade, having the following data components:
    Demographic, clinical, pathology, treatment, outcomes, and genomic data: Collected from a variety of sources including clinical notes, radiology report, and pathology reports and has served as a source for multiple published papers on radiogenomics, outcomes prediction, and other areas.
    Pre-operative dynamic contrast enhanced (DCE)-MRI: Downloaded from PACS systems and de-identified for The Cancer Imaging Archive (TCIA) release. These include axial breast MRI images acquired by 1.5T or 3T scanners in the prone positions. Following MRI sequences are shared in DICOM format: a non-fat saturated T1-weighted sequence, a fat-saturated gradient echo T1-weighted pre-contrast sequence, and mostly three to four post-contrast sequences.
    Locations of lesions in DCE-MRI: Annotations on the DCE-MRI images by radiologists.
    Imaging features from DCE-MRI: A set of 529 computer-extracted imaging features by inhouse software. These features represent a variety of imaging characteristics including size, shape, texture, and enhancement of both the tumor and the surrounding tissue, which is combined of features commonly published in the literature, as well as the features developed in our lab.""")
    dataset.set_field(category="dataset_description", row_index=13, header="Value",
                      value="There is a moderate association between tumour molecular biomarkers and algorithmically assessed imaging features.")
    dataset.set_field(category="dataset_description", row_index=14, header="Value", value="breast")
    dataset.set_field(category="dataset_description", row_index=15, header="Value", value="Machine-learning")
    dataset.set_field(category="dataset_description", row_index=16, header="Value",
                      value="""We analysed a set of 922 patients with invasive breast cancer and pre-operative MRI. The MRIs were analysed by a computer algorithm to extract 529 features of the tumour and the surrounding tissue. Machine-learning-based models based on the imaging features were trained using a portion of the data (461 patients) to predict the following molecular, genomic, and proliferation characteristics: tumour surrogate molecular subtype, oestrogen receptor, progesterone receptor and human epidermal growth factor status, as well as a tumour proliferation marker (Ki-67). Trained models were evaluated on the set of the remaining 461 patients.""")
    dataset.set_field(category="dataset_description", row_index=17, header="Value",
                      value="Dynamic contrast-enhanced magnetic resonance images of breast cancer patients with tumor locations (Duke-Breast-Cancer-MRI)")
    dataset.set_field(category="dataset_description", row_index=19, header="Value", value="Saha, Ashirbani")
    dataset.set_field(category="dataset_description", row_index=19, header="Value 2", value="Harowicz, Michael R")
    dataset.set_field(category="dataset_description", row_index=19, header="Value 3", value="Grimm, Lars J")
    dataset.set_field(category="dataset_description", row_index=19, header="Value 4", value="Kim, Connie E")
    dataset.set_field(category="dataset_description", row_index=19, header="Value 5", value="Ghate, Sujata V")
    dataset.set_field(category="dataset_description", row_index=19, header="Value 6", value="Walsh, Ruth")
    dataset.set_field(category="dataset_description", row_index=19, header="Value 7", value="Mazurowski, Maciej A")
    dataset.set_field(category="dataset_description", row_index=20, header="Value",
                      value="https://orcid.org/0000-0002-7650-1720")
    dataset.set_field(category="dataset_description", row_index=20, header="Value 2",
                      value="https://orcid.org/0000-0002-8002-5210")
    dataset.set_field(category="dataset_description", row_index=20, header="Value 3",
                      value="https://orcid.org/0000-0002-3865-3352")
    dataset.set_field(category="dataset_description", row_index=20, header="Value 4",
                      value="https://orcid.org/0000-0003-0730-0551")
    dataset.set_field(category="dataset_description", row_index=20, header="Value 5",
                      value="https://orcid.org/0000-0003-1889-982X")
    dataset.set_field(category="dataset_description", row_index=20, header="Value 6",
                      value="https://orcid.org/0000-0002-2164-2761")
    dataset.set_field(category="dataset_description", row_index=20, header="Value 7",
                      value="https://orcid.org/0000-0003-4202-8602")
    dataset.set_field(category="dataset_description", row_index=21, header="Value", value="Duke University")
    dataset.set_field(category="dataset_description", row_index=21, header="Value 2", value="Duke University")
    dataset.set_field(category="dataset_description", row_index=21, header="Value 3", value="Duke University")
    dataset.set_field(category="dataset_description", row_index=21, header="Value 4", value="Duke University")
    dataset.set_field(category="dataset_description", row_index=21, header="Value 5", value="Duke University")
    dataset.set_field(category="dataset_description", row_index=21, header="Value 6", value="Duke University")
    dataset.set_field(category="dataset_description", row_index=21, header="Value 7", value="Duke University")
    dataset.set_field(category="dataset_description", row_index=22, header="Value", value="Researcher")
    dataset.set_field(category="dataset_description", row_index=22, header="Value 2", value="Researcher")
    dataset.set_field(category="dataset_description", row_index=22, header="Value 3", value="Researcher")
    dataset.set_field(category="dataset_description", row_index=22, header="Value 4", value="Researcher")
    dataset.set_field(category="dataset_description", row_index=22, header="Value 5", value="Researcher")
    dataset.set_field(category="dataset_description", row_index=22, header="Value 6", value="Researcher")
    dataset.set_field(category="dataset_description", row_index=22, header="Value 7", value="Researcher")
    dataset.set_field(category="dataset_description", row_index=24, header="Value", value="source")
    dataset.set_field(category="dataset_description", row_index=25, header="Value", value="IsDescribedBy")
    dataset.set_field(category="dataset_description", row_index=26, header="Value",
                      value="9d70fd9f-bfb9-424d-9c7c-9db1ec6a9df9")
    dataset.set_field(category="dataset_description", row_index=27, header="Value", value="12L digital twin UUID")
    dataset.set_field(category="dataset_description", row_index=29, header="Value", value="1")
    dataset.set_field(category="dataset_description", row_index=30, header="Value", value="1")

    dataset.save_metadata(save_dir)
    return dataset


def set_subject_metadata(subject):
    subject_metadata = {
        "subject id": subject,
        "subject experimental group": "experimental",
        "age": "041Y",
        "sex": "F",
        "species": "human",
        "strain": "tissue",
        "age category": "middle adulthood"
    }

    return subject_metadata


def set_sample_metadata(subject, sample):
    sample_metadata = {
        "sample id": sample,
        "subject id": subject,
        "sample experimental group": "experimental",
        "sample type": "tissue",
        "sample anatomical location": "breast tissue",
    }
    return sample_metadata


def add_data(dataset, source_path, subject, sample, save_dir):
    subject_metadata = set_subject_metadata(subject)
    sample_metadata = set_sample_metadata(subject, sample)

    dataset.add_primary_data(source_path=source_path, subject=subject, sample=sample, sds_parent_dir=save_dir,
                             overwrite=True,
                             sample_metadata=sample_metadata,
                             subject_metadata=subject_metadata)
    return dataset


if __name__ == '__main__':
    save_dir = "./logs/primary_dataset/"

    # Creating a SDS dataset from template
    dataset = Dataset()
    dataset.load_from_template(version="2.0.0")

    # Filling dataset.
    add_dataset_description(dataset, save_dir=save_dir)
    subject = "sub-1.3.6.1.4.1.14519.5.2.1.186051521067863971269584893740842397538"
    sample = "sam-1.3.6.1.4.1.14519.5.2.1.175414966301645518238419021688341658582"
    add_data(dataset, source_path= os.path.join("../resources", subject, sample), subject=subject, sample=sample, save_dir=save_dir)
