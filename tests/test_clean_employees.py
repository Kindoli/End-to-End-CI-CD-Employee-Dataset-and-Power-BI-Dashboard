
import pandas as pd
import pytest

from src.clean_employees import clean_employees


# ---------------------------------------------------------
# HELPER FUNCTION
# ---------------------------------------------------------
# Create a valid employee DataFrame for reuse across tests.
# Individual tests can override specific values to simulate
# missing data, duplicates, or invalid records.

def sample_employee_data():
    return pd.DataFrame({
        "EmployeeID": ["E001", "E002", "E003"],
        "Name": ["Alice", "Bob", "Charlie"],
        "Gender": ["Female", "Male", "Male"],
        "Department": ["HR", "Finance", "IT"],
        "Salary": ["$50,000.00", "$60,000.00", "$70,000.00"],
        "Location": [
            "New York, USA",
            "Wellington, NZ",
            "California, USA",
        ],
        "Start_Date": [
            "04/03/2020",
            "24/05/2019",
            "03/05/2019",
        ],
    })


# ---------------------------------------------------------
# TEST 1: REMOVE MISSING EMPLOYEE IDs
# ---------------------------------------------------------

def test_removes_missing_employee_ids():
    df = sample_employee_data()

    df.loc[1, "EmployeeID"] = None

    result = clean_employees(df)

    assert len(result) == 2
    assert result["EmployeeID"].notna().all()


# ---------------------------------------------------------
# TEST 2: REMOVE BLANK EMPLOYEE IDs
# ---------------------------------------------------------

def test_removes_blank_employee_ids():
    df = sample_employee_data()

    df.loc[1, "EmployeeID"] = "   "

    result = clean_employees(df)

    assert len(result) == 2
    assert result["EmployeeID"].ne("").all()


# ---------------------------------------------------------
# TEST 3: REMOVE DUPLICATE EMPLOYEE IDs
# ---------------------------------------------------------

def test_removes_duplicate_employee_ids():
    df = sample_employee_data()

    # Duplicate E001 with a different department.
    duplicate = df.iloc[[0]].copy()
    duplicate["Department"] = "IT"

    df = pd.concat([df, duplicate], ignore_index=True)

    result = clean_employees(df)

    assert result["EmployeeID"].is_unique
    assert len(result) == 3

    # The first occurrence should be retained.
    e001 = result.loc[result["EmployeeID"] == "E001"]

    assert e001.iloc[0]["Department"] == "HR"


# ---------------------------------------------------------
# TEST 4: TRIM WHITESPACE FROM TEXT VALUES
# ---------------------------------------------------------

def test_trims_text_values():
    df = sample_employee_data()

    df.loc[0, "EmployeeID"] = " E001 "
    df.loc[0, "Department"] = " Finance "
    df.loc[0, "Gender"] = " Female "

    result = clean_employees(df)

    employee = result.loc[
        result["EmployeeID"] == "E001"
    ].iloc[0]

    assert employee["EmployeeID"] == "E001"
    assert employee["Department"] == "Finance"
    assert employee["Gender"] == "Female"


# ---------------------------------------------------------
# TEST 5: REQUIRE EMPLOYEE ID
# ---------------------------------------------------------

def test_requires_employee_id():
    df = sample_employee_data().drop(
        columns=["EmployeeID"]
    )

    with pytest.raises(ValueError, match="EmployeeID"):
        clean_employees(df)


# ---------------------------------------------------------
# TEST 6: REPLACE MISSING GENDER
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "missing_gender",
    [None, "", "   ", "NULL", "null"],
)
def test_replaces_missing_gender(missing_gender):
    df = sample_employee_data()

    df.loc[0, "Gender"] = missing_gender

    result = clean_employees(df)

    assert (
        result.loc[0, "Gender"]
        == "not willing to disclose"
    )


# ---------------------------------------------------------
# TEST 7: REPLACE MISSING DEPARTMENT WITH FINANCE
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "missing_department",
    [None, "", "   ", "NULL", "null"],
)
def test_replaces_missing_department(missing_department):
    df = sample_employee_data()

    df.loc[0, "Department"] = missing_department

    result = clean_employees(df)

    assert result.loc[0, "Department"] == "Finance"


# ---------------------------------------------------------
# TEST 8: REMOVE RECORDS WITH MISSING SALARY
# ---------------------------------------------------------

@pytest.mark.parametrize(
    "missing_salary",
    [None, "", "   ", "NULL", "N/A"],
)
def test_removes_missing_salary(missing_salary):
    df = sample_employee_data()

    df.loc[0, "Salary"] = missing_salary

    result = clean_employees(df)

    assert "E001" not in result["EmployeeID"].values
    assert len(result) == 2


# ---------------------------------------------------------
# TEST 9: EXTRACT COUNTRY FROM LOCATION
# ---------------------------------------------------------

def test_extracts_country_from_location():
    df = sample_employee_data()

    result = clean_employees(df)

    assert "Country" in result.columns

    assert result.loc[0, "Country"] == "USA"
    assert result.loc[1, "Country"] == "NZ"
    assert result.loc[2, "Country"] == "USA"


# ---------------------------------------------------------
# TEST 10: COUNTRY EXTRACTION HANDLES NEWLINES
# ---------------------------------------------------------

def test_extracts_country_from_multiline_location():
    df = sample_employee_data()

    df.loc[0, "Location"] = (
        "3 Redmond Way\n"
        "Bellevue, WA\n"
        "USA"
    )

    result = clean_employees(df)

    assert result.loc[0, "Country"] == "USA"


# ---------------------------------------------------------
# TEST 11: EXTRACT YEAR FROM START DATE
# ---------------------------------------------------------

def test_extracts_year_from_start_date():
    df = sample_employee_data()

    result = clean_employees(df)

    assert "Year" in result.columns

    assert result.loc[0, "Year"] == 2020
    assert result.loc[1, "Year"] == 2019
    assert result.loc[2, "Year"] == 2019


# ---------------------------------------------------------
# TEST 12: INVALID START DATE PRODUCES MISSING YEAR
# ---------------------------------------------------------

def test_invalid_start_date_produces_missing_year():
    df = sample_employee_data()

    df.loc[0, "Start_Date"] = "invalid-date"

    result = clean_employees(df)

    assert pd.isna(result.loc[0, "Year"])


# ---------------------------------------------------------
# TEST 13: STANDARDIZE COLUMN NAMES
# ---------------------------------------------------------

def test_standardizes_column_names():
    df = sample_employee_data()

    df = df.rename(columns={
        "EmployeeID": " EmployeeID ",
        "Start_Date": "Start Date",
    })

    result = clean_employees(df)

    assert "EmployeeID" in result.columns
    assert "Start_Date" in result.columns


# ---------------------------------------------------------
# TEST 14: OUTPUT DOES NOT CONTAIN BLANK SALARIES
# ---------------------------------------------------------

def test_output_contains_no_blank_salaries():
    df = sample_employee_data()

    df.loc[0, "Salary"] = ""

    result = clean_employees(df)

    salary_values = result["Salary"].astype(str).str.strip()

    assert salary_values.ne("").all()
    assert salary_values.str.upper().ne("NULL").all()


# ---------------------------------------------------------
# TEST 15: REQUIRED COLUMNS ARE VALIDATED
# ---------------------------------------------------------

def test_requires_all_cleaning_columns():
    df = pd.DataFrame({
        "EmployeeID": ["E001"],
        "Department": ["Finance"],
    })

    with pytest.raises(ValueError, match="Required columns"):
        clean_employees(df)
#
