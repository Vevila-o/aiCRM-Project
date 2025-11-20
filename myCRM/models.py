from django.db import models

# Create your models here.

##交易明細表
class TransactionDetail(models.Model):
    transactionid = models.IntegerField(db_column='transactionID', primary_key=True)  # Field name made lowercase.
    productid = models.IntegerField(db_column='productID', blank=True, null=True)  # Field name made lowercase.
    quantity = models.IntegerField(blank=True, null=True)
    subtotal = models.IntegerField(blank=True, null=True)
    transdate = models.DateField(db_column='transDate', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'transaction_detail'

##交易主表
class Transaction(models.Model):
    transactionid = models.IntegerField(db_column='transactionID', primary_key=True)  # Field name made lowercase.
    customerid = models.IntegerField(db_column='customerID', blank=True, null=True)  # Field name made lowercase.
    transdate = models.DateField(db_column='transDate', blank=True, null=True)  # Field name made lowercase.
    totalprice = models.FloatField(db_column='totalPrice', blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'transaction'

##商品
class Product(models.Model):
    productid = models.IntegerField(db_column='productID', primary_key=True)  # Field name made lowercase.
    productname = models.CharField(db_column='productName', max_length=100, blank=True, null=True)  # Field name made lowercase.
    productprice = models.FloatField(db_column='productPrice', blank=True, null=True)  # Field name made lowercase.
    categoryid = models.CharField(db_column='categoryID', max_length=10, blank=True, null=True)  # Field name made lowercase.
    brand = models.CharField(max_length=45, blank=True, null=True)
    statue = models.CharField(max_length=45, blank=True, null=True)

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
        
        
##RFM分數表
class RFMscore(models.Model):
    customerID = models.IntegerField(db_column='customerID', primary_key=True)  # 顧客ID
    rScore = models.IntegerField(db_column='rScore', blank=True, null=True)  # Recency 分數
    fScore = models.IntegerField(db_column='fScore', blank=True, null=True)  # Frequency 分數
    mScore = models.IntegerField(db_column='mScore', blank=True, null=True)  # Monetary 分數
    RFMscore = models.IntegerField(db_column='RFMscore', blank=True, null=True)  # 總 RFM 分數
    categoryID = models.IntegerField(db_column='categoryID', blank=True, null=True)  # 商品類別ID
    RFMupdate = models.DateTimeField(db_column='RFMupdate', blank=True, null=True)  # 更新時間

    class Meta:
        managed = False
        db_table = 'rfm_score'   
        
        
## 員工表

class User(models.Model):
    userid = models.IntegerField(db_column='userID', primary_key=True)  # Field name made lowercase.
    username = models.CharField(db_column='userName', max_length=45, blank=True, null=True)  # Field name made lowercase.
    employeeid = models.IntegerField(db_column='employeeID', blank=True, null=True)  # Field name made lowercase.
    password = models.CharField(max_length=45, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'user'
        
## rfm分級
class CustomerCategory(models.Model):
    categoryid = models.IntegerField(db_column='categoryID', primary_key=True)  # Field name made lowercase.
    customercategory = models.CharField(db_column='customerCategory', max_length=45, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'customer_category'


## ai建議
class AiSuggection(models.Model):
    suggectid = models.AutoField(db_column='suggectID', primary_key=True)  # 主鍵
    categoryID = models.IntegerField(db_column='CategoryID', blank=True, null=True)  
    userID = models.CharField(db_column='userID', max_length=45, blank=True, null=True) 
    aiRecommedGuideline = models.CharField(db_column='aiRecommedGuideline', max_length=1000, blank=True, null=True)  
    expectedResults = models.CharField(db_column='expectedResults', max_length=1000, blank=True, null=True)  
    suggestDate = models.DateTimeField(db_column='suggestDate', blank=True, null=True)  

    class Meta:
        managed = False   
        db_table = 'ai_suggection'

## ai聊天紀錄
class ChatRecord(models.Model):
    chatID = models.AutoField(db_column='chatID', primary_key=True)  # 主鍵

    user = models.ForeignKey(
        User,
        models.DO_NOTHING,
        db_column='userID',
        blank=True,
        null=True,
    )

    categoryID = models.IntegerField(db_column='categoryID', blank=True, null=True)  # 1-7 顧客價值類型
    userContent = models.TextField(db_column='userContent', blank=True, null=True)   # 使用者問題
    aiContent = models.TextField(db_column='aiContent', blank=True, null=True)       # AI 回覆

    class Meta:
        managed = False
        db_table = 'chat_record'
        
## 商品類別
class ProductCategory(models.Model):
    categoryid = models.IntegerField(db_column='categoryID', primary_key=True)  # Field name made lowercase.
    categoryname = models.CharField(db_column='categoryName', max_length=45, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'product_category'

## 優惠券
class Campaign(models.Model):
    campaignid = models.IntegerField(db_column='campaignID', primary_key=True)  # Field name made lowercase.
    customerid = models.IntegerField(db_column='customerID', blank=True, null=True)  # Field name made lowercase.
    type = models.CharField(max_length=45, blank=True, null=True)
    givetime = models.DateTimeField(db_column='giveTime', blank=True, null=True)  # Field name made lowercase.
    starttime = models.DateTimeField(db_column='startTime', blank=True, null=True)  # Field name made lowercase.
    endtime = models.DateTimeField(db_column='endTime', blank=True, null=True)  # Field name made lowercase.
    isuse = models.CharField(db_column='isUse', max_length=10, blank=True, null=True)  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'campaign'
