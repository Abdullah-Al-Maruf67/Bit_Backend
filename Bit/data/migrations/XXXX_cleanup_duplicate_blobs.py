from django.db import migrations

def cleanup_duplicate_blobs(apps, schema_editor):
    Blob = apps.get_model('data', 'Blob')
    # Get all blobs grouped by sha1_hash and file_path
    seen = set()
    duplicates = []
    for blob in Blob.objects.all():
        key = (blob.sha1_hash, blob.file_path)
        if key in seen:
            duplicates.append(blob.id)
        else:
            seen.add(key)
    
    # Delete duplicates
    if duplicates:
        Blob.objects.filter(id__in=duplicates).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('data', '0004_alter_blob_sha1_hash'),  # Update this to your last migration
    ]

    operations = [
        migrations.RunPython(cleanup_duplicate_blobs),
    ] 