from django.db import models

# Create your models here.

##交易明細表
class TransactionDetail(models.Model):
    transactionid = models.IntegerField(db_column='transactionID', blank=True, null=True)  # Field name made lowercase.
    customerid = models.IntegerField(db_column='customerID', blank=True, null=True)  # Field name made lowercase.
    productid = models.IntegerField(db_column='productID', blank=True, null=True)  # Field name made lowercase.
    quantity = models.IntegerField(blank=True, null=True)
    subtotal = models.IntegerField(blank=True, null=True)
    transdate = models.DateField(db_column='transDate', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'transaction_detail'

##交易主表
class Transction(models.Model):
    transactionid = models.IntegerField(db_column='transactionID', blank=True, null=True)  # Field name made lowercase.
    customerid = models.IntegerField(db_column='customerID', blank=True, null=True)  # Field name made lowercase.
    transdate = models.DateField(db_column='transDate', blank=True, null=True)  # Field name made lowercase.
    totalprice = models.FloatField(db_column='totalPrice', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'transction'

##商品
class Product(models.Model):
    productid = models.IntegerField(db_column='productID', blank=True, null=True)  # Field name made lowercase.
    productname = models.CharField(db_column='productName', max_length=512, blank=True, null=True)  # Field name made lowercase.
    productprice = models.IntegerField(db_column='productPrice', blank=True, null=True)  # Field name made lowercase.
    brand = models.CharField(max_length=512, blank=True, null=True)
    statue = models.CharField(max_length=512, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'product'

##顧客
class Customer(models.Model):
    customerid = models.IntegerField(db_column='customerID', blank=True, null=True)  # Field name made lowercase.
    customername = models.CharField(db_column='customerName', max_length=512, blank=True, null=True)  # Field name made lowercase.
    gender = models.CharField(max_length=512, blank=True, null=True)
    customerbirth = models.DateField(db_column='customerBirth', blank=True, null=True)  # Field name made lowercase.
    customerregion = models.CharField(db_column='customerRegion', max_length=512, blank=True, null=True)  # Field name made lowercase.
    customerjoinday = models.DateField(db_column='customerJoinDay', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'customer'

# Django Auth User Table        
class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.IntegerField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.IntegerField()
    is_active = models.IntegerField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'