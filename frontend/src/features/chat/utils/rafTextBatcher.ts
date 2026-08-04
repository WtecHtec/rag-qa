export interface AnimationFrameScheduler {
  request(callback: FrameRequestCallback): number;
  cancel(frameId: number): void;
}

const browserScheduler: AnimationFrameScheduler = {
  request: (callback) => window.requestAnimationFrame(callback),
  cancel: (frameId) => window.cancelAnimationFrame(frameId),
};

/**
 * 将高频 token 合并到浏览器下一帧再提交，避免每个网络分片都触发一次 React 渲染。
 */
export class RafTextBatcher {
  private pending = "";
  private frameId: number | null = null;

  constructor(
    private readonly onFlush: (content: string) => void,
    private readonly scheduler: AnimationFrameScheduler = browserScheduler,
  ) {}

  push(content: string): void {
    this.pending += content;
    if (this.frameId !== null) return;
    this.frameId = this.scheduler.request(() => {
      this.frameId = null;
      this.flush();
    });
  }

  flush(): void {
    if (this.frameId !== null) {
      this.scheduler.cancel(this.frameId);
      this.frameId = null;
    }
    if (!this.pending) return;
    const content = this.pending;
    this.pending = "";
    this.onFlush(content);
  }

  clear(): void {
    if (this.frameId !== null) this.scheduler.cancel(this.frameId);
    this.frameId = null;
    this.pending = "";
  }
}
