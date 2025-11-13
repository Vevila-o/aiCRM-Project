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
class Transaction(models.Model):
    transactionid = models.IntegerField(db_column='transactionID', blank=True, null=True)  # Field name made lowercase.
    customerid = models.IntegerField(db_column='customerID', blank=True, null=True)  # Field name made lowercase.
    transdate = models.DateField(db_column='transDate', blank=True, null=True)  # Field name made lowercase.
    totalprice = models.FloatField(db_column='totalPrice', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'transaction'

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
    customerid = models.IntegerField(db_column='customerID', primary_key=True)  # Field name made lowercase.
    customername = models.CharField(db_column='customerName', max_length=50, db_collation='utf8mb4_0900_ai_ci', blank=True, null=True)  # Field name made lowercase.
    gender = models.CharField(max_length=10, db_collation='utf8mb4_0900_ai_ci', blank=True, null=True)
    customerbirth = models.DateField(db_column='customerBirth', blank=True, null=True)  # Field name made lowercase.
    customerregion = models.CharField(db_column='customerRegion', max_length=100, db_collation='utf8mb4_0900_ai_ci', blank=True, null=True)  # Field name made lowercase.
    customerjoinday = models.DateField(db_column='customerJoinDay', blank=True, null=True)  # Field name made lowercase.
    categoryid = models.CharField(db_column='categoryID', max_length=10, blank=True, null=True)  # Field name made lowercase.
    customerlastdaybuy = models.DateField(db_column='customerLastDayBuy', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'customer'