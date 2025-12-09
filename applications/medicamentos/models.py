from django.db import models

# Create your models here.
class NomencladorIpsPromedi(models.Model):
    codigo = models.IntegerField(
        unique=True,
        blank=False,
        null=False
    )
    porcentaje_promedi = models.FloatField(
        blank=False,
        null=False
    )
    class Meta:
        db_table= 'nomenclador_ips_promedi'

    @staticmethod
    def obtener_porcentaje_por_codigo(codigo):
        try:
            return NomencladorIpsPromedi.objects.get(codigo=codigo).porcentaje_promedi
        except NomencladorIpsPromedi.DoesNotExist:
            print('codigo no encontrado', codigo)
            return 0
