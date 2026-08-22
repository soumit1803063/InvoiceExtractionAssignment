interface EditableTextFieldProps {
  label: string;
  value: string;
  placeholder?: string;
  isDisabled: boolean;
  isInvalid?: boolean;
  invalidMessage?: string;
  alignEnd?: boolean;
  onValueChange: (nextValue: string) => void;
}

export function EditableTextField({
  label,
  value,
  placeholder,
  isDisabled,
  isInvalid = false,
  invalidMessage,
  alignEnd = false,
  onValueChange
}: EditableTextFieldProps) {
  return (
    <label className="field">
      <span className="field__label">{label}</span>
      <input
        className={`field__input${alignEnd ? ' field__input--end' : ''}${isInvalid ? ' field__input--invalid' : ''}`}
        value={value}
        placeholder={placeholder ?? ''}
        disabled={isDisabled}
        aria-invalid={isInvalid}
        onChange={(event) => onValueChange(event.target.value)}
      />
      {isInvalid && invalidMessage ? <span className="field__error">{invalidMessage}</span> : null}
    </label>
  );
}
