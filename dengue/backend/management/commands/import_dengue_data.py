import os
from django.core.management.base import BaseCommand
from django.db import transaction
import pandas as pd
from your_app.models import DengueCase, Barangay

class Command(BaseCommand):
    help = 'Import dengue cases from Excel file'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'excel_file',
            type=str,
            help='Path to the Excel file to import'
        )
        parser.add_argument(
            '--year',
            type=int,
            required=True,
            help='Year of the data (e.g., 2021)'
        )
        parser.add_argument(
            '--sheet',
            type=str,
            default='Sheet1',
            help='Sheet name to import from (default: Sheet1)'
        )

    def handle(self, *args, **options):
        excel_file_path = options['excel_file']
        year = options['year']
        sheet_name = options['sheet']
        
        if not os.path.exists(excel_file_path):
            self.stderr.write(self.style.ERROR(f"File not found: {excel_file_path}"))
            return
        
        try:
            self.import_dengue_data(excel_file_path, year, sheet_name)
            self.stdout.write(
                self.style.SUCCESS(f'Successfully imported dengue data for {year}')
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Error importing data: {str(e)}'))

    def import_dengue_data(self, excel_file_path, year, sheet_name):
        # Read Excel file
        df = pd.read_excel(excel_file_path, sheet_name=sheet_name)
        
        cases_created = 0
        errors = []
        
        with transaction.atomic():
            for index, row in df.iterrows():
                try:
                    barangay_name = str(row.get('BARANGAY', '')).strip()
                    if not barangay_name or barangay_name == 'nan':
                        continue
                    
                    # Get or create barangay
                    barangay, created = Barangay.objects.get_or_create(
                        name=barangay_name,
                        defaults={'name': barangay_name}
                    )
                    
                    if created:
                        self.stdout.write(f"Created new barangay: {barangay_name}")
                    
                    # Process each week column
                    for week_num in range(1, 53):
                        week_column = f'WEEK {week_num}'
                        if week_column in row:
                            try:
                                num_cases = int(row[week_column]) if pd.notna(row[week_column]) else 0
                            except (ValueError, TypeError):
                                num_cases = 0
                            
                            # Only create record if there are cases
                            if num_cases > 0:
                                # Check if record already exists
                                existing_case = DengueCase.objects.filter(
                                    barangay=barangay,
                                    year_reported=year,
                                    week_reported=week_num
                                ).first()
                                
                                if existing_case:
                                    # Update existing record
                                    existing_case.num_cases = num_cases
                                    existing_case.save()
                                else:
                                    # Create new record
                                    DengueCase.objects.create(
                                        barangay=barangay,
                                        year_reported=year,
                                        week_reported=week_num,
                                        num_cases=num_cases
                                    )
                                cases_created += 1
                    
                except Exception as e:
                    errors.append(f"Row {index + 2}: {str(e)}")  # +2 because Excel rows start at 1 and header is row 1
                    self.stderr.write(self.style.WARNING(f"Error processing row {index + 2}: {str(e)}"))
        
        if errors:
            self.stdout.write(self.style.WARNING(f"Completed with {len(errors)} errors"))
            for error in errors:
                self.stdout.write(self.style.WARNING(error))
        
        self.stdout.write(
            self.style.SUCCESS(f'Processed {cases_created} dengue case records')
        )