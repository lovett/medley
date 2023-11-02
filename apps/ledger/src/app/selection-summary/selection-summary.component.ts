import { Component } from '@angular/core';
import { LedgerService } from '../ledger.service';

@Component({
  selector: 'app-selection-summary',
  templateUrl: './selection-summary.component.html',
  styleUrls: ['./selection-summary.component.css']
})
export class SelectionSummaryComponent {
    amount: number = 0;
    count: number = 0;

    constructor(private ledgerService: LedgerService) {
        this.ledgerService.selection$.subscribe(amount => {
            if (amount == Infinity) {
                this.amount = 0;
                this.count = 0;
                return;
            }

            if (amount < 1) {
                this.amount -= amount;
                this.count -= 1;
                return;
            }

            this.amount += amount;
            this.count += 1;
        });
    }
}
