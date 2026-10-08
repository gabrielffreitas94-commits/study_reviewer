import 'package:flutter/material.dart';

enum SyncStatus {
  synced,
  pendingSync,
  offline,
}

class SyncStatusBadge extends StatefulWidget {
  final SyncStatus status;
  final String? customLabel;
  final int? pendingCount;

  const SyncStatusBadge({
    super.key,
    required this.status,
    this.customLabel,
    this.pendingCount,
  });

  @override
  State<SyncStatusBadge> createState() => _SyncStatusBadgeState();
}

class _SyncStatusBadgeState extends State<SyncStatusBadge>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulseController;
  late final Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1000),
    );

    _pulseAnimation = Tween<double>(begin: 0.5, end: 1.0).animate(
      CurvedAnimation(
        parent: _pulseController,
        curve: Curves.easeInOut,
      ),
    );

    if (widget.status == SyncStatus.pendingSync) {
      _pulseController.repeat(reverse: true);
    }
  }

  @override
  void didUpdateWidget(SyncStatusBadge oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.status == SyncStatus.pendingSync) {
      if (!_pulseController.isAnimating) {
        _pulseController.repeat(reverse: true);
      }
    } else {
      if (_pulseController.isAnimating) {
        _pulseController.stop();
        _pulseController.value = 1.0;
      }
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final disableAnimations = MediaQuery.of(context).disableAnimations;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    final (Color bgColor, Color fgColor, IconData icon, String defaultLabel) =
        switch (widget.status) {
      SyncStatus.synced => (
          isDark ? const Color(0xFF1B3820) : const Color(0xFFE8F5E9),
          isDark ? const Color(0xFF81C784) : const Color(0xFF2E7D32),
          Icons.check_circle_outline,
          'Sincronizado',
        ),
      SyncStatus.pendingSync => (
          isDark ? const Color(0xFF3E2C00) : const Color(0xFFFFF8E1),
          isDark ? const Color(0xFFFFD54F) : const Color(0xFFE65100),
          Icons.sync,
          widget.pendingCount != null && widget.pendingCount! > 0
              ? '${widget.pendingCount} pendente(s)'
              : 'Aguardando rede',
        ),
      SyncStatus.offline => (
          isDark ? const Color(0xFF2C2C2C) : const Color(0xFFEEEEEE),
          isDark ? const Color(0xFFB0B0B0) : const Color(0xFF424242),
          Icons.cloud_off_outlined,
          'Offline',
        ),
    };

    final displayText = widget.customLabel ?? defaultLabel;

    Widget badgeContent = Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: fgColor.withOpacity(0.3),
          width: 1.0,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            icon,
            size: 14,
            color: fgColor,
          ),
          const SizedBox(width: 6),
          Text(
            displayText,
            style: TextStyle(
              color: fgColor,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );

    // Âmbar pulsante para respostas pendentes aguardando rede
    if (widget.status == SyncStatus.pendingSync && !disableAnimations) {
      badgeContent = FadeTransition(
        opacity: _pulseAnimation,
        child: badgeContent,
      );
    }

    return Semantics(
      label: 'Status de conexão e sincronização: $displayText',
      container: true,
      child: badgeContent,
    );
  }
}
