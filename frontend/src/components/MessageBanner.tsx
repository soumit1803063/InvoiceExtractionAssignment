import type { ReactNode } from 'react';

export type MessageTone = 'info' | 'success' | 'warning' | 'danger';

interface MessageBannerProps {
  tone: MessageTone;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}

export function MessageBanner({ tone, title, children, action }: MessageBannerProps) {
  return (
    <div className={`banner banner--${tone}`} role={tone === 'danger' ? 'alert' : 'status'}>
      <div className="banner__body">
        <p className="banner__title">{title}</p>
        {children ? <div className="banner__detail">{children}</div> : null}
      </div>
      {action ? <div className="banner__action">{action}</div> : null}
    </div>
  );
}
