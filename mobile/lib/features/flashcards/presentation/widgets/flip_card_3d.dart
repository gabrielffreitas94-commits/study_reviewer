import 'dart:math' as math;
import 'package:flutter/material.dart';

class FlipCard3D extends StatefulWidget {
  final Widget front;
  final Widget back;
  final bool? isFlipped;
  final VoidCallback? onFlip;
  final Duration duration;

  const FlipCard3D({
    super.key,
    required this.front,
    required this.back,
    this.isFlipped,
    this.onFlip,
    this.duration = const Duration(milliseconds: 300),
  });

  @override
  State<FlipCard3D> createState() => _FlipCard3DState();
}

class _FlipCard3DState extends State<FlipCard3D>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _animation;
  bool _internalFlipped = false;

  bool get _isCardFlipped => widget.isFlipped ?? _internalFlipped;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: widget.duration,
      value: _isCardFlipped ? 1.0 : 0.0,
    );

    _animation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _controller,
        curve: Curves.easeInOut,
      ),
    );
  }

  @override
  void didUpdateWidget(FlipCard3D oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.isFlipped != null && widget.isFlipped != oldWidget.isFlipped) {
      if (widget.isFlipped!) {
        _controller.forward();
      } else {
        _controller.reverse();
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _toggle() {
    final disableAnimations = MediaQuery.of(context).disableAnimations;

    if (widget.isFlipped == null) {
      setState(() {
        _internalFlipped = !_internalFlipped;
      });
      if (disableAnimations) {
        _controller.value = _internalFlipped ? 1.0 : 0.0;
      } else {
        if (_internalFlipped) {
          _controller.forward();
        } else {
          _controller.reverse();
        }
      }
    }

    widget.onFlip?.call();
  }

  @override
  Widget build(BuildContext context) {
    final disableAnimations = MediaQuery.of(context).disableAnimations;

    // Respeito estrito a prefers-reduced-motion: transição instantânea sem giro 3D
    if (disableAnimations) {
      return GestureDetector(
        onTap: _toggle,
        behavior: HitTestBehavior.opaque,
        child: _isCardFlipped ? widget.back : widget.front,
      );
    }

    return GestureDetector(
      onTap: _toggle,
      behavior: HitTestBehavior.opaque,
      child: AnimatedBuilder(
        animation: _animation,
        builder: (context, _) {
          final angle = _animation.value * math.pi;
          final isFront = angle <= math.pi / 2;

          final transform = Matrix4.identity()
            ..setEntry(3, 2, 0.001) // Matriz de perspectiva 3D
            ..rotateY(angle);

          return RepaintBoundary(
            child: Transform(
              transform: transform,
              alignment: Alignment.center,
              child: isFront
                  ? widget.front
                  : Transform(
                      // Rotação de corte a 90 graus para evitar flicker e espelhamento
                      transform: Matrix4.identity()..rotateY(math.pi),
                      alignment: Alignment.center,
                      child: widget.back,
                    ),
            ),
          );
        },
      ),
    );
  }
}
