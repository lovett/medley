import { Component, Input, Output, EventEmitter } from '@angular/core';

@Component({
  selector: 'ledger-delete-button',
  templateUrl: './delete-button.component.html',
  styleUrls: ['./delete-button.component.css']
})
export class DeleteButtonComponent {
    @Input() resourceName = 'record'
    @Output() deletionConfirmed = new EventEmitter<string>();
    confirm() {
        if (confirm(`Really delete this ${this.resourceName}?`)) {
            this.deletionConfirmed.emit();
        }
    }
}
