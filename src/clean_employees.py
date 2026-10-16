
from pathlib import Path
import argparse
import pandas as pd


def clean_employees(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean employee records using explicit, testable rules.

    Cleaning rules:
    1. Standardize column names.
    2. Remove records with missing EmployeeID.
    3. Trim whitespace from text fields.
    4. Replace missing Gender with 'not willing to disclose'.
    5. Replace missing or NULL Department with 'Finance'.
    6. Remove records where Salary is blank or missing.
    7. Extract the country code from Location into a Country column.
    8. Extract the year from Start_Date into a Year column.
    9. Keep only one record per EmployeeID.
    """

    # Work on a copy so that the original DataFrame is not modified.
    df = df.copy()

    # ---------------------------------------------------------
    # 1. STANDARDIZE COLUMN NAMES
    # ---------------------------------------------------------
    # Remove leading/trailing spaces from column names.
    # Replace spaces within column names with underscores.
    #
    # Example:
    # "Start Date" becomes "Start_Date"
    # " EmployeeID " becomes "EmployeeID"

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.replace(r"\s+", "_", regex=True)
    )

    # ---------------------------------------------------------
    # 2. CHECK REQUIRED COLUMNS
    # ---------------------------------------------------------
    # These columns are necessary for the cleaning rules below.
    # Stop execution with a clear error if any are missing.

    required_columns = [
        "EmployeeID",
        "Gender",
        "Department",
        "Salary",
        "Location",
        "Start_Date",
    ]

    missing_columns = [
        col for col in required_columns if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Required columns are missing: {missing_columns}"
        )

    # ---------------------------------------------------------
    # 3. CLEAN EMPLOYEE IDs
    # ---------------------------------------------------------
    # Convert IDs to strings and remove surrounding whitespace.
    # Remove records where EmployeeID is missing or blank.

    df["EmployeeID"] = (
        df["EmployeeID"].astype("string").str.strip()
    )

    df = df.dropna(subset=["EmployeeID"])

    df = df[df["EmployeeID"] != ""].copy()

    # ---------------------------------------------------------
    # 4. TRIM WHITESPACE FROM TEXT COLUMNS
    # ---------------------------------------------------------
    # Remove unnecessary spaces from text fields.
    #
    # Example:
    # "  Engineering  " becomes "Engineering"
    # "  Female " becomes "Female"

    for col in df.select_dtypes(
        include=["object", "string"]
    ).columns:
        df[col] = df[col].str.strip()

    # ---------------------------------------------------------
    # 5. CLEAN GENDER
    # ---------------------------------------------------------
    # Replace missing values, empty strings, and the literal
    # text "NULL" with "not willing to disclose".
    #
    # The replacement is case-insensitive for "NULL".

    df["Gender"] = (
        df["Gender"].astype("string").str.strip()
    )

    missing_gender = (
        df["Gender"].isna()
        | df["Gender"].eq("")
        | df["Gender"].str.upper().eq("NULL").fillna(False)
    )

    df.loc[
        missing_gender, "Gender"
    ] = "not willing to disclose"

    # ---------------------------------------------------------
    # 6. CLEAN DEPARTMENT
    # ---------------------------------------------------------
    # Replace missing values, blank strings, and literal "NULL"
    # with "Finance".
    #
    # Existing valid department names remain unchanged.

    df["Department"] = (
        df["Department"].astype("string").str.strip()
    )

    missing_department = (
        df["Department"].isna()
        | df["Department"].eq("")
        | df["Department"].str.upper().eq("NULL").fillna(False)
    )

    df.loc[missing_department, "Department"] = "Finance"

    # ---------------------------------------------------------
    # 7. REMOVE RECORDS WITH BLANK SALARY
    # ---------------------------------------------------------
    # Remove rows where Salary is missing, empty, or contains
    # common missing-value markers.
    #
    # This checks whether a salary was provided. It does not
    # convert the remaining salary strings to numeric values.

    salary_text = df["Salary"].astype("string").str.strip()

    valid_salary = (
        salary_text.notna()
        & salary_text.ne("")
        & ~salary_text.str.upper().isin(
            ["NULL", "N/A", "NA"]
        )
    )

    df = df.loc[valid_salary].copy()

    # ---------------------------------------------------------
    # 8. EXTRACT COUNTRY FROM LOCATION
    # ---------------------------------------------------------
    # Create a new Country column by extracting USA or NZ when
    # that country code appears at the end of Location.
    #
    # Examples:
    # "3 Redmond Way, Bellevue, WA, USA" -> "USA"
    # "8 Parliament Lane - Wellington, NZ" -> "NZ"
    #
    # The expression also handles newline characters from
    # addresses containing HTML line breaks.
    #
    # Locations not ending in USA or NZ will have a missing
    # Country value. Review these records separately if needed.

    location_text = (
        df["Location"].astype("string").str.strip()
    )

    df["Country"] = location_text.str.extract(
        r"\b(USA|NZ)\s*$",
        flags=0,
        expand=False,
    )

    # ---------------------------------------------------------
    # 9. EXTRACT YEAR FROM START_DATE
    # ---------------------------------------------------------
    # Parse dates using dayfirst=True because the supplied data
    # includes dates such as 24/05/2019.
    #
    # Create a new Year column containing only the year.
    #
    # Example:
    # "24/05/2019" -> 2019
    #
    # Invalid or missing dates become <NA> in the Year column.
    # They are not automatically removed from the dataset.

    parsed_dates = pd.to_datetime(
        df["Start_Date"],
        errors="coerce",
        dayfirst=True,
    )

    df["Year"] = parsed_dates.dt.year.astype("Int64")

    # ---------------------------------------------------------
    # 10. REMOVE DUPLICATE EMPLOYEE IDs
    # ---------------------------------------------------------
    # Keep the first remaining record for each EmployeeID.
    #
    # This happens after removing blank salaries, so a record
    # with a blank salary will not be retained ahead of a valid
    # record for the same employee.
    #
    # IMPORTANT:
    # This assumes EmployeeID uniquely identifies an employee.

    df = df.drop_duplicates(
        subset=["EmployeeID"],
        keep="first",
    )

    # Reset row numbering after filtering and deduplication.
    return df.reset_index(drop=True)


def main():
    # ---------------------------------------------------------
    # 11. DEFINE COMMAND-LINE ARGUMENTS
    # ---------------------------------------------------------
    # These arguments allow the script to be reused locally
    # and in GitHub Actions without changing the Python code.
    #
    # Example:
    # python -m src.clean_employees \
    #   --input data/raw/Employee-data.csv \
    #   --output data/processed/employees_clean.csv

    parser = argparse.ArgumentParser(
        description="Clean and transform employee data."
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to the raw employee CSV file.",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Path where the cleaned CSV will be saved.",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    # ---------------------------------------------------------
    # 12. CHECK THAT THE INPUT FILE EXISTS
    # ---------------------------------------------------------
    # Provide a clear error instead of a confusing file error.

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file does not exist: {input_path}"
        )

    # ---------------------------------------------------------
    # 13. LOAD THE RAW DATA
    # ---------------------------------------------------------
    # Read the source CSV into a pandas DataFrame.
    # keep_default_na=True allows common missing-value markers
    # to be interpreted as missing values.

    df = pd.read_csv(input_path)

    # ---------------------------------------------------------
    # 14. APPLY THE CLEANING RULES
    # ---------------------------------------------------------
    cleaned = clean_employees(df)

    # ---------------------------------------------------------
    # 15. CREATE THE OUTPUT DIRECTORY
    # ---------------------------------------------------------
    # Create any missing parent directories automatically.
    #
    # Example:
    # data/processed/ will be created if it does not exist.

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ---------------------------------------------------------
    # 16. SAVE THE CLEANED DATASET
    # ---------------------------------------------------------
    # Save without the pandas index because it is not a business
    # column in the employee dataset.

    cleaned.to_csv(
        output_path,
        index=False,
    )

    # ---------------------------------------------------------
    # 17. PRINT A SUMMARY FOR PIPELINE LOGS
    # ---------------------------------------------------------
    # These messages appear in your terminal or GitHub Actions
    # logs, making it easier to monitor the cleaning process.

    print(f"Input records: {len(df)}")
    print(f"Output records: {len(cleaned)}")
    print(f"Records removed: {len(df) - len(cleaned)}")
    print(f"Output columns: {list(cleaned.columns)}")
    print(f"Output file: {output_path}")


# Run main() only when this file is executed as a script.
if __name__ == "__main__":
    main()
