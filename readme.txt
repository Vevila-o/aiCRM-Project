需要下載的套件
pandas numpy keras  matplotlib pymysql catboost python-dotenv PyTorch

套件部分特別下載指令
pip install -U scikit-learn
pip install torch
pip install requests python-dotenv

database: ai_crm



10/31 createsuperuser
account: ze098
password: Vivi4519345

11/1 
// MySQL
1. 安裝 pymysql
  pip install 
  
2. setting.py更改設定
 *import pymysql
  pymysql.install_as_MySQLdb()
 
 *DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "your database name",
        "USER": "your database user",
        "PASSWORD": "your password",
        "HOST": "",
        "PORT": "3306",
    }
 }

 //出現bug >> 原先有先建立一個表單但輸入指令
  >>python manage.py inspectdb > myCRM/models.py
  >> models.py 的東西被刪除了
  >> admin.py error: ImportError: cannot import name 'VIP_inform' from 'myCRM.models' (C:\CRM\myCRM\models.py)

  <修正Test>
  
  將原先宣告的VIP_inform全都註解掉，admin.py也註解化
  >> 再次輸入指令
  -- error: 'cryptography' package is required for sha256_password or caching_sha2_password auth methods
  >> 安裝缺少套件
  >> pip install cryptography
  --成功下載
  >> 系統自動跑 python manage.py inspectdb > myCRM/models.py
  >> python manage.py migrate
  -- error: django.db.utils.OperationalError: (1045, "Access denied for user 'your database user'@'localhost' (using password: YES)")
  [setting.py] 發現沒填寫 database名稱 跟帳號密碼
      >>"HOST": "localhost", 新增localhost
  >>再次嘗試 python manage.py migrate 
  -- <成功更新資料>

  // 取用mysql 資料
  [views.py]
  class Customer(models.Model):
	# 此 model 對應現有的 mysql `customer` 表，設定 managed=False 避免 Django 嘗試建立此表
	id = models.IntegerField(primary_key=True)
	name = models.CharField(max_length=45, blank=True, null=True)
	phone = models.IntegerField(blank=True, null=True)
	purchase = models.IntegerField(blank=True, null=True)
	purchase_product = models.CharField(max_length=500, blank=True, null=True)

	class Meta:
		db_table = 'customer'
		managed = False

	def __str__(self):
		return self.name or str(self.id)

11/12
1. mysql問題

//python orm 處理mysql的資料庫問題，因為migrate一直出錯
>>python manage.py migrate --fake 
讓django不要在建資料表

//要將資料庫的表能來處理orm要將資料表的相關內容寫進models.py
>> python manage.py inspectdb
會出現連接的資料表，選擇要用的來複製上去

2. 新增service層
//未來模型不能都在views.py裡寫
此曾用來寫其他的function，之後再到views裡來操作

//views.py中增加import
>>from .services.(服務.py) import 服務裡的function

11/13 
catboost
ai完成個別流失機率預測
前端匯入

11/14
前端修正、後端rfm、登入控制、ai訊問框