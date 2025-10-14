
from django.db import models
from django.contrib.auth.models import User

import json
from applications.core.models import BaseAbstractWithUser

class PresupuestoHistorial(BaseAbstractWithUser):
    presupuesto = models.ForeignKey("Presupuesto", on_delete=models.CASCADE, related_name="historiales")
    fecha = models.DateTimeField(auto_now_add=True) 
    datos = models.JSONField()  # guardamos todos los datos en formato JSON

    def __str__(self):
        return f"Historial Presupuesto {self.presupuesto.id} - {self.fecha}"
    

class Prestacion(BaseAbstractWithUser):
    nombre = models.CharField(max_length=255)
    codigo = models.CharField(max_length=50, blank=True, null=True)  # si usás nomenclador
    gastos = models.DecimalField(max_digits=14, decimal_places=2)
    especialista = models.DecimalField(max_digits=14, decimal_places=2)

    def total(self):
        return self.gastos+ self.especialista
    def __str__(self):
        return f"{self.nombre} - ${self.precio}"
    


class Presupuesto(BaseAbstractWithUser):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('concretado', 'Concretado'),
        ('no_concretado', 'No Concretado'),
    ]

    
    # Datos del paciente
    paciente_nombre = models.CharField(max_length=200)
    paciente_dni = models.CharField(max_length=20, blank=True, null=True)
    paciente_edad = models.PositiveIntegerField(blank=True, null=True)
    paciente_direccion = models.CharField(max_length=255, blank=True, null=True)
    paciente_telefono = models.CharField(max_length=50, blank=True, null=True)
    obra_social = models.CharField(max_length=100, blank=True, null=True)
    paciente_email=models.EmailField(max_length=100, blank=True, null=True)
    # Datos médicos
    medico = models.CharField(max_length=200, blank=True, null=True)
    diagnostico = models.CharField(max_length=255, blank=True, null=True)
    episodio = models.CharField(max_length=200,blank=True,null=True)   
    # Seguimiento
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    motivo_no_concretado = models.TextField(blank=True, null=True)


    # Usuario que lo cargó 

    @property    
    def subtotal(self):
        return sum([item.importe for item in self.items.all()])
    @property    
    def total(self):
        return sum([item.subtotal for item in self.items.all()])
    
    @property    
    def iva(self):
        return sum([item.iva for item in self.items.all()])

    def __str__(self):
        return f"Presupuesto {self.id} - {self.paciente_nombre}"

class Pago(BaseAbstractWithUser):
    MEDIOS_PAGO = [
        ("efectivo", "Efectivo"),
        ("transferencia", "Transferencia"),
        ("tarjeta", "Tarjeta"),
    ]

    TIPO_CAJA = [
        ("cajaa", "Caja A"),
        ("cajab", "Caja B"),
        ("cajac", "Caja C"),
    ]
    presupuesto = models.ForeignKey(Presupuesto, on_delete=models.CASCADE, related_name="pagos")
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    medio_pago = models.CharField(max_length=50, choices=MEDIOS_PAGO)
    observaciones = models.CharField(max_length=300, null=True,blank=True)
    caja = models.CharField(max_length=50,choices= TIPO_CAJA,  blank=True, null=True) 
    fecha = models.DateTimeField(auto_now_add=True) 
    def __str__(self):
        return f"Pago {self.monto} - {self.presupuesto.id}"

class PresupuestoItem(models.Model):
    presupuesto = models.ForeignKey(
        "Presupuesto", 
        related_name="items", 
        on_delete=models.CASCADE
    )
    # Datos de la prestación en el momento de generar el presupuesto
    codigo = models.CharField(max_length=50, blank=True, null=True)
    matricula = models.CharField(max_length=50, blank=True, null=True)
    prestacion = models.CharField(max_length=255, blank=True, null=True)  # texto libre
    cantidad = models.IntegerField(default=1)
    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0)   # precio unitario congelado
    importe = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # cantidad * precio
    iva = models.DecimalField(max_digits=10, decimal_places=2, default=0)      # monto de IVA
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0) # total con IVA
    TIPO_CHOICES = [
        ('gastos', 'Gastos'),
        ('especialista', 'Especialista'),
        ('todo', 'Todo'),
    ]
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default='gastos'
    )
    def __str__(self):
        return f"{self.prestacion} x{self.cantidad}"