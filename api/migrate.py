from django.core.management import execute_from_command_line
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bankproject.settings')
django.setup()

def handler(request):
    """Vercel function to run Django migrations"""
    try:
        execute_from_command_line(['manage.py', 'migrate'])
        return {
            'statusCode': 200,
            'body': 'Migrations completed successfully'
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f'Migration failed: {str(e)}'
        } 