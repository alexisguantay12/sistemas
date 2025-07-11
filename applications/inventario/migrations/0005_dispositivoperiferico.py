# Generated by Django 3.2.25 on 2025-07-01 12:59

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('inventario', '0004_servidor'),
    ]

    operations = [
        migrations.CreateModel(
            name='DispositivoPeriferico',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('tipo', models.CharField(choices=[('IMPRESORA', 'Impresora'), ('ESCANER', 'Escáner')], max_length=20)),
                ('marca', models.CharField(max_length=100)),
                ('modelo', models.CharField(blank=True, max_length=100)),
                ('nro_serie', models.CharField(blank=True, max_length=100)),
                ('conexion', models.CharField(blank=True, help_text='Ej: USB, Red, Wi-Fi', max_length=50)),
                ('ip', models.CharField(blank=True, max_length=20)),
                ('estado', models.CharField(choices=[('FUNCIONANDO', 'Funcionando'), ('EN_REPARACION', 'En reparación'), ('FUERA_DE_SERVICIO', 'Fuera de servicio')], max_length=20)),
                ('observaciones', models.TextField(blank=True)),
                ('ultima_revision', models.DateField(blank=True, null=True)),
                ('ubicacion', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='inventario.ubicacion')),
                ('user_deleted', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='dispositivoperiferico_user_deleted', to=settings.AUTH_USER_MODEL, verbose_name='eliminado por')),
                ('user_made', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='dispositivoperiferico_user_made', to=settings.AUTH_USER_MODEL, verbose_name='hecho por')),
                ('user_updated', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='dispositivoperiferico_user_updated', to=settings.AUTH_USER_MODEL, verbose_name='actualizado por')),
            ],
            options={
                'verbose_name': 'Periférico',
                'verbose_name_plural': 'Periféricos',
            },
        ),
    ]
