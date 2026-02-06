
import pytest
from services.device_classifier import DeviceClassifier, DeviceSignals, DeviceType, ConfidenceLevel

class TestDeviceClassifier:
    
    def setup_method(self):
        self.classifier = DeviceClassifier()

    def test_classify_firewall_high_confidence(self):
        """Test high confidence firewall classification via SNMP & OUI"""
        signals = DeviceSignals(
            ip_address="192.168.1.1",
            snmp_sys_descr="Cisco ASA 5506-X Adaptive Security Appliance",
            manufacturer="Cisco Systems",
            open_ports=[22, 443]
        )
        
        result = self.classifier.classify(signals)
        
        assert result.device_type == DeviceType.FIREWALL
        assert result.confidence == ConfidenceLevel.HIGH
        assert result.score >= 60 # SNMP weight
        assert "sysDescr match" in result.reasoning

    def test_classify_switch_mac_only(self):
        """Test switch classification via MAC OUI (Medium confidence)"""
        signals = DeviceSignals(
            ip_address="10.0.0.2",
            manufacturer="Cisco Systems",
            open_ports=[22], # Generic port
            snmp_sys_descr=None
        )
        # Cisco default is Switch in VENDOR_MAP, but scores 25 (Medium)
        result = self.classifier.classify(signals)
        
        assert result.device_type == DeviceType.SWITCH
        assert result.confidence == ConfidenceLevel.MEDIUM # 25 points
        assert result.score == 25

    def test_classify_printer_ports(self):
        """Test printer classification via ports"""
        signals = DeviceSignals(
            ip_address="192.168.1.50",
            open_ports=[9100, 515, 80],
            manufacturer="Unknown"
        )
        
        result = self.classifier.classify(signals)
        
        assert result.device_type == DeviceType.PRINTER
        assert result.score >= 15 # Port weight

    def test_classify_server_hostname(self):
        """Test server classification via hostname + ports"""
        signals = DeviceSignals(
            ip_address="10.10.10.10",
            hostname="web-prod-01",
            open_ports=[80, 443, 3306] # Web + MySQL
        )
        
        result = self.classifier.classify(signals)
        
        # Hostname (10) + Ports (15) = 25 (Medium)
        assert result.device_type == DeviceType.SERVER
        assert result.score >= 25 
        assert result.confidence == ConfidenceLevel.MEDIUM

    def test_classify_mobile_device(self):
        """Test mobile device (Apple OUI + No Ports)"""
        signals = DeviceSignals(
            ip_address="192.168.50.50",
            manufacturer="Apple, Inc.",
            open_ports=[]
        )
        
        result = self.classifier.classify(signals)
        
        # Apple (25) + No Ports Mobile Bonus (10) = 35
        assert result.device_type == DeviceType.MOBILE
        assert result.score >= 35

    def test_unknown_device(self):
        """Test unknown device with no useful signals"""
        signals = DeviceSignals(
            ip_address="1.2.3.4",
            open_ports=[9999], # Random port
            manufacturer="GenericChinaplastic"
        )
        
        result = self.classifier.classify(signals)
        
        assert result.device_type == DeviceType.UNKNOWN
        assert result.confidence == ConfidenceLevel.LOW
