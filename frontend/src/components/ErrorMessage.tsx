interface Props {
  message: string;
}

export function ErrorMessage({ message }: Props) {
  if (!message) {
    return null;
  }
  return <div className="error-message">{message}</div>;
}
