from random import randrange
import base64
import time

customizedBase64Charset = 'mV/1onByu7ZzPO5vYw2xe0U8AK3fHgbcCpFdkl6W+RShMGDjia4tQLEsIJrTX9qN='
encodeCustomizedBase64Indices = [
      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 62, 0, 0, 0, 63,
      52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 0, 0, 0, 64, 0, 0,
      0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14,
      15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 0, 0, 0, 0, 0,
      0, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40,
      41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 0, 0, 0, 0, 0,
      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
      0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
    ]

def passwordEncryption(password, inputRnd=None, option={'type': 'mcpwv3'}):
    rnd = inputRnd
    if rnd == None:
        rnd = randrange(10000)

    offset = rnd % 65
    cryptData = password
    if option['type'] == 'mcpwv3':
        now = int(time.time())
        cryptData = '%d %s' % (now, password)
    cryptData = base64.b64encode(cryptData.encode('utf8')).decode('utf8')
    
    encryptPwd = ''
    for c in cryptData:
        newIndex = (encodeCustomizedBase64Indices[ord(c)] + offset) % 65
        encryptPwd = encryptPwd + customizedBase64Charset[newIndex]

    return encryptPwd, rnd
    

#pwd, rnd = passwordEncryption('1QAZ2wsx')
#print('Password: ' + pwd)
#print('Random Number: ' + str(rnd))