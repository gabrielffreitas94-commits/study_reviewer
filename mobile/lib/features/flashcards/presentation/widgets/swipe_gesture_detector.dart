import 'package:flutter/material.dart';

class SwipeGestureDetector extends StatefulWidget {
  final Widget child;
  final VoidCallback onSwipeLeft;
  final double distanceThreshold;
  final double velocityThreshold;
  final Duration exitDuration;

  const SwipeGestureDetector({
    super.key,
    required this.child,
    required this.onSwipeLeft,
    this.distanceThreshold = 80.0,
    this.velocityThreshold = 300.0,
    this.exitDuration = const Duration(milliseconds: 130), // 120-150ms micro-animação GPU
  });

  @override
  State<SwipeGestureDetector> createState() => _SwipeGestureDetectorState();
}

class _SwipeGestureDetectorState extends State<SwipeGestureDetector>
    with SingleTickerProviderStateMixin {
  late final AnimationController _exitController;
  late final Animation<Offset> _slideAnimation;
  late final Animation<double> _fadeAnimation;

  double _accumulatedDelta = 0.0;
  bool _isExiting = false;

  @override
  void initState() {
    super.initState();
    _exitController = AnimationController(
      vsync: this,
      duration: widget.exitDuration,
    );

    _slideAnimation = Tween<Offset>(
      begin: Offset.zero,
      end: const Offset(-1.5, 0.0),
    ).animate(
      CurvedAnimation(
        parent: _exitController,
        curve: Curves.fastOutSlowIn,
      ),
    );

    _fadeAnimation = Tween<double>(
      begin: 1.0,
      end: 0.0,
    ).animate(
      CurvedAnimation(
        parent: _exitController,
        curve: Curves.easeIn,
      ),
    );

    _exitController.addStatusListener((status) {
      if (status == AnimationStatus.completed) {
        widget.onSwipeLeft();
        _exitController.reset();
        setState(() {
          _isExiting = false;
          _accumulatedDelta = 0.0;
        });
      }
    });
  }

  @override
  void dispose() {
    _exitController.dispose();
    super.dispose();
  }

  void _onHorizontalDragStart(DragStartDetails details) {
    if (_isExiting) {
      return;
    }
    _accumulatedDelta = 0.0;
  }

  void _onHorizontalDragUpdate(DragUpdateDetails details) {
    if (_isExiting) {
      return;
    }
    _accumulatedDelta += details.primaryDelta ?? 0.0;
  }

  void _onHorizontalDragEnd(DragEndDetails details) {
    if (_isExiting) {
      return;
    }

    final velocity = details.primaryVelocity ?? 0.0;
    // Condição de disparo: deslocamento para a esquerda >= 80dp e velocidade > 300dp/s
    final meetsDistance = _accumulatedDelta <= -widget.distanceThreshold;
    final meetsVelocity = velocity <= -widget.velocityThreshold;

    if (meetsDistance || (meetsVelocity && _accumulatedDelta < -20)) {
      final disableAnimations = MediaQuery.of(context).disableAnimations;
      if (disableAnimations) {
        _accumulatedDelta = 0.0;
        widget.onSwipeLeft();
      } else {
        setState(() {
          _isExiting = true;
        });
        _exitController.forward();
      }
    } else {
      _accumulatedDelta = 0.0;
    }
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onHorizontalDragStart: _onHorizontalDragStart,
      onHorizontalDragUpdate: _onHorizontalDragUpdate,
      onHorizontalDragEnd: _onHorizontalDragEnd,
      behavior: HitTestBehavior.opaque,
      child: RepaintBoundary(
        child: SlideTransition(
          position: _slideAnimation,
          child: FadeTransition(
            opacity: _fadeAnimation,
            child: widget.child,
          ),
        ),
      ),
    );
  }
}
