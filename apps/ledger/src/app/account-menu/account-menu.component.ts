import { Component, Input, OnInit } from '@angular/core';
import { FormControl } from '@angular/forms';
import { LedgerService } from '../ledger.service';
import { Account } from '../models/account';
import { AccountList } from '../types/AccountList';

@Component({
  selector: 'ledger-account-menu[control]',
  templateUrl: './account-menu.component.html',
  styleUrls: ['./account-menu.component.css'],
})
export class AccountMenuComponent implements OnInit {
    @Input() control!: FormControl;
    @Input() fieldId?: string;
    @Input() label?: string;
    @Input() account?: Account;
    @Input() disabledValue?: Account;

    accounts: Account[] = [];

    constructor(
        private ledgerService: LedgerService
    ) {}

    ngOnInit() {
        this.ledgerService.getAccounts().subscribe({
            next: (accountList: AccountList) => {
                for (const jsonAccount of accountList.accounts) {
                    const  a = Account.fromJson(jsonAccount);
                    if (a.closed_on && a.uid !== this.control.value) {
                        continue;
                    }
                    this.accounts.push(a);
                }
            },
            error: (err: Error) => console.log(err),
        });
    }

    compareFn(a1: Account, a2: Account): boolean {
        if (a1 && a2) {
            return a1.uid === a2.uid;
        }
        return false;
    }
}
