import subprocess
import sys
import csv
import io

def run_gcloud_command(command, check=True):
    """Runs a gcloud command and returns its stdout."""
    try:
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=check,
            shell=True # Using shell=True for simplicity as gcloud is a complex command
        )
        return process.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e.cmd}", file=sys.stderr)
        print(f"Stderr: {e.stderr}", file=sys.stderr)
        sys.exit(1)

def find_active_billing_account():
    """Finds and returns the display name and ID of an active billing account."""
    command = "gcloud beta billing accounts list --format='csv(displayName,name,open)'"
    output = run_gcloud_command(command)

    if not output:
        return None, None

    csv_reader = csv.reader(io.StringIO(output))
    # Skip header
    try:
        next(csv_reader)
    except StopIteration:
        # Handle empty output
        return None, None


    for row in csv_reader:
        if len(row) == 3 and row[2] == 'True' and "Trial Billing Account" in row[0]:
            return row[0], row[1] # displayName, name (ID)

    return None, None

def get_current_project():
    """Gets the current gcloud project ID."""
    # Redirect stderr to avoid printing an error message when no project is set.
    # We don't check=True here because a non-zero exit code is expected if not set.
    command = "gcloud config get-value project"
    return run_gcloud_command(command, check=False)

def select_project():
    """Lists available projects and prompts the user to select one."""
    print("Fetching available projects...")
    command = "gcloud projects list --format='csv(projectId,name)'"
    output = run_gcloud_command(command)

    if not output:
        print("No projects found.", file=sys.stderr)
        return None

    csv_reader = csv.reader(io.StringIO(output))
    try:
        header = next(csv_reader)
    except StopIteration:
        print("No projects found.", file=sys.stderr)
        return None
    
    projects = list(csv_reader)

    if not projects:
        print("No projects found.", file=sys.stderr)
        return None

    print("Please select a project:")
    for i, (project_id, name) in enumerate(projects):
        print(f"  {i + 1}: {project_id} ({name})")

    while True:
        try:
            selection = input(f"Enter a number (1-{len(projects)}): ")
            selection_index = int(selection) - 1
            if 0 <= selection_index < len(projects):
                return projects[selection_index][0] # Return the project ID
            else:
                print("Invalid selection. Please try again.", file=sys.stderr)
        except ValueError:
            print("Invalid input. Please enter a number.", file=sys.stderr)

def link_billing_account(project_id, billing_account_id):
    """Links the billing account to the project."""
    command = f"gcloud beta billing projects link {project_id} --billing-account {billing_account_id}"
    run_gcloud_command(command)

def main():
    """Main function to find and link the billing account."""
    print("Finding an active billing account...")
    display_name, billing_id = find_active_billing_account()

    if not billing_id:
        print("Error: No active billing account with 'Trial Billing Account' in the name found.", file=sys.stderr)
        sys.exit(1)

    print(f"Found billing account: {display_name} ({billing_id})")

    print("Finding current project...")
    project_id = get_current_project()

    if not project_id:
        print("No active gcloud project found. Let's select one.")
        project_id = select_project()
        if not project_id:
            print("No project selected. Exiting.", file=sys.stderr)
            sys.exit(1)
        
        print(f"Setting project '{project_id}' as current...")
        run_gcloud_command(f"gcloud config set project {project_id}")
        # Re-fetch to confirm
        project_id = get_current_project()

    if not project_id:
         print("Failed to set project. Exiting.", file=sys.stderr)
         sys.exit(1)

    print(f"Using project: {project_id}")

    print(f"Linking project {project_id} to billing account {display_name} ({billing_id})...")
    link_billing_account(project_id, billing_id)

    print("Successfully linked project.")

if __name__ == "__main__":
    main()
