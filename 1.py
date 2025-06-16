import pystun3

# 获取公网 IP 和 NAT 类型
public_ip, nat_type = pystun3.get_ip_info()

print("Public IP:", public_ip)
print("NAT Type:", nat_type)
