from flask import Flask, render_template, jsonify, request
import subprocess
import platform
import socket
import requests
import time
import threading
import psutil
import json
from datetime import datetime
import speedtest
import ping3
import dns.resolver

app = Flask(__name__)

class NetworkDiagnostics:
    def __init__(self):
        self.results = {}
    
    def get_network_interfaces(self):
        """Get all network interfaces and their details"""
        interfaces = {}
        for interface, addrs in psutil.net_if_addrs().items():
            interface_info = {
                'addresses': [],
                'status': 'up' if interface in psutil.net_if_stats() and psutil.net_if_stats()[interface].isup else 'down'
            }
            
            for addr in addrs:
                if addr.family == socket.AF_INET:  # IPv4
                    interface_info['addresses'].append({
                        'type': 'IPv4',
                        'address': addr.address,
                        'netmask': addr.netmask,
                        'broadcast': addr.broadcast
                    })
                elif addr.family == socket.AF_INET6:  # IPv6
                    interface_info['addresses'].append({
                        'type': 'IPv6',
                        'address': addr.address,
                        'netmask': addr.netmask
                    })
            
            interfaces[interface] = interface_info
        
        return interfaces
    
    def get_network_stats(self):
        """Get network usage statistics"""
        stats = psutil.net_io_counters()
        return {
            'bytes_sent': stats.bytes_sent,
            'bytes_recv': stats.bytes_recv,
            'packets_sent': stats.packets_sent,
            'packets_recv': stats.packets_recv,
            'errin': stats.errin,
            'errout': stats.errout,
            'dropin': stats.dropin,
            'dropout': stats.dropout
        }
    
    def ping_test(self, host='8.8.8.8', count=4):
        """Perform ping test"""
        results = []
        total_time = 0
        successful_pings = 0
        
        for i in range(count):
            try:
                delay = ping3.ping(host, timeout=5)
                if delay is not None:
                    delay_ms = delay * 1000
                    results.append({
                        'sequence': i + 1,
                        'time': round(delay_ms, 2),
                        'status': 'success'
                    })
                    total_time += delay_ms
                    successful_pings += 1
                else:
                    results.append({
                        'sequence': i + 1,
                        'time': None,
                        'status': 'timeout'
                    })
            except Exception as e:
                results.append({
                    'sequence': i + 1,
                    'time': None,
                    'status': f'error: {str(e)}'
                })
        
        packet_loss = ((count - successful_pings) / count) * 100
        avg_time = total_time / successful_pings if successful_pings > 0 else 0
        
        return {
            'host': host,
            'results': results,
            'packet_loss': round(packet_loss, 2),
            'average_time': round(avg_time, 2),
            'successful_pings': successful_pings,
            'total_pings': count
        }
    
    def traceroute_test(self, host='8.8.8.8'):
        """Perform traceroute test"""
        try:
            if platform.system().lower() == 'windows':
                cmd = ['tracert', '-h', '30', host]
            else:
                cmd = ['traceroute', '-m', '30', host]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            hops = []
            lines = result.stdout.split('\n')
            
            for line in lines:
                if line.strip() and not line.startswith('traceroute') and not line.startswith('Tracing'):
                    hops.append(line.strip())
            
            return {
                'host': host,
                'hops': hops,
                'status': 'success' if result.returncode == 0 else 'error'
            }
        except Exception as e:
            return {
                'host': host,
                'hops': [],
                'status': f'error: {str(e)}'
            }
    
    def dns_lookup_test(self, domain='google.com'):
        """Perform DNS lookup test"""
        results = {}
        
        try:
            # A record
            a_records = dns.resolver.resolve(domain, 'A')
            results['A'] = [str(record) for record in a_records]
        except Exception as e:
            results['A'] = f'Error: {str(e)}'
        
        try:
            # AAAA record (IPv6)
            aaaa_records = dns.resolver.resolve(domain, 'AAAA')
            results['AAAA'] = [str(record) for record in aaaa_records]
        except Exception as e:
            results['AAAA'] = f'Error: {str(e)}'
        
        try:
            # MX record
            mx_records = dns.resolver.resolve(domain, 'MX')
            results['MX'] = [str(record) for record in mx_records]
        except Exception as e:
            results['MX'] = f'Error: {str(e)}'
        
        return {
            'domain': domain,
            'records': results
        }
    
    def speed_test(self):
        """Perform comprehensive speed test"""
        try:
            st = speedtest.Speedtest()
            st.get_best_server()
            
            # Download speed
            download_speed = st.download() / 1_000_000  # Convert to Mbps
            
            # Upload speed
            upload_speed = st.upload() / 1_000_000  # Convert to Mbps
            
            # Ping
            ping_result = st.results.ping
            
            # Server info
            server_info = st.results.server
            
            return {
                'download_speed': round(download_speed, 2),
                'upload_speed': round(upload_speed, 2),
                'ping': round(ping_result, 2),
                'server': {
                    'name': server_info['name'],
                    'country': server_info['country'],
                    'sponsor': server_info['sponsor'],
                    'host': server_info['host'],
                    'distance': round(server_info['d'], 2)
                },
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def bandwidth_monitor(self, duration=10, interval=1):
        """Monitor bandwidth usage over time"""
        initial_stats = psutil.net_io_counters()
        measurements = []
        
        for i in range(duration):
            time.sleep(interval)
            current_stats = psutil.net_io_counters()
            
            bytes_sent_rate = (current_stats.bytes_sent - initial_stats.bytes_sent) / ((i + 1) * interval)
            bytes_recv_rate = (current_stats.bytes_recv - initial_stats.bytes_recv) / ((i + 1) * interval)
            
            measurements.append({
                'timestamp': datetime.now().isoformat(),
                'download_rate_mbps': round((bytes_recv_rate * 8) / 1_000_000, 2),
                'upload_rate_mbps': round((bytes_sent_rate * 8) / 1_000_000, 2)
            })
        
        return measurements
    
    def check_connectivity(self):
        """Check connectivity to various services"""
        test_hosts = [
            {'name': 'Google DNS', 'host': '8.8.8.8', 'port': 53},
            {'name': 'Cloudflare DNS', 'host': '1.1.1.1', 'port': 53},
            {'name': 'Google HTTP', 'host': 'google.com', 'port': 80},
            {'name': 'Google HTTPS', 'host': 'google.com', 'port': 443},
            {'name': 'Facebook', 'host': 'facebook.com', 'port': 443},
            {'name': 'Twitter', 'host': 'twitter.com', 'port': 443}
        ]
        
        results = []
        
        for test in test_hosts:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                
                start_time = time.time()
                result = sock.connect_ex((test['host'], test['port']))
                end_time = time.time()
                
                if result == 0:
                    status = 'Connected'
                    response_time = round((end_time - start_time) * 1000, 2)
                else:
                    status = 'Failed'
                    response_time = None
                
                sock.close()
                
                results.append({
                    'name': test['name'],
                    'host': test['host'],
                    'port': test['port'],
                    'status': status,
                    'response_time': response_time
                })
                
            except Exception as e:
                results.append({
                    'name': test['name'],
                    'host': test['host'],
                    'port': test['port'],
                    'status': f'Error: {str(e)}',
                    'response_time': None
                })
        
        return results

# Initialize diagnostics
diagnostics = NetworkDiagnostics()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/interfaces')
def get_interfaces():
    """Get network interfaces"""
    return jsonify(diagnostics.get_network_interfaces())

@app.route('/api/stats')
def get_stats():
    """Get network statistics"""
    return jsonify(diagnostics.get_network_stats())

@app.route('/api/ping/<host>')
def ping_host(host):
    """Ping a specific host"""
    count = request.args.get('count', 4, type=int)
    return jsonify(diagnostics.ping_test(host, count))

@app.route('/api/traceroute/<host>')
def traceroute_host(host):
    """Traceroute to a specific host"""
    return jsonify(diagnostics.traceroute_test(host))

@app.route('/api/dns/<domain>')
def dns_lookup(domain):
    """DNS lookup for a domain"""
    return jsonify(diagnostics.dns_lookup_test(domain))

@app.route('/api/speedtest')
def speed_test():
    """Perform speed test"""
    return jsonify(diagnostics.speed_test())

@app.route('/api/bandwidth-monitor')
def bandwidth_monitor():
    """Monitor bandwidth usage"""
    duration = request.args.get('duration', 10, type=int)
    interval = request.args.get('interval', 1, type=int)
    return jsonify(diagnostics.bandwidth_monitor(duration, interval))

@app.route('/api/connectivity')
def check_connectivity():
    """Check connectivity to various services"""
    return jsonify(diagnostics.check_connectivity())

@app.route('/api/full-diagnosis')
def full_diagnosis():
    """Perform complete network diagnosis"""
    results = {
        'timestamp': datetime.now().isoformat(),
        'interfaces': diagnostics.get_network_interfaces(),
        'stats': diagnostics.get_network_stats(),
        'ping_google': diagnostics.ping_test('8.8.8.8'),
        'ping_cloudflare': diagnostics.ping_test('1.1.1.1'),
        'dns_lookup': diagnostics.dns_lookup_test('google.com'),
        'connectivity': diagnostics.check_connectivity(),
        'speed_test': diagnostics.speed_test()
    }
    
    return jsonify(results)

if __name__ == '__main__':
    print("Starting Network Diagnostics Server...")
    print("Access the application at: http://localhost:5000")
    print("\nAvailable API endpoints:")
    print("- GET /api/interfaces - Network interfaces")
    print("- GET /api/stats - Network statistics") 
    print("- GET /api/ping/<host> - Ping test")
    print("- GET /api/traceroute/<host> - Traceroute")
    print("- GET /api/dns/<domain> - DNS lookup")
    print("- GET /api/speedtest - Speed test")
    print("- GET /api/connectivity - Connectivity check")
    print("- GET /api/full-diagnosis - Complete diagnosis")
    
    app.run(host='0.0.0.0', port=5000, debug=True)