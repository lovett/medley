import { Component, OnInit, OnDestroy } from '@angular/core';
import { FormGroup, FormBuilder, Validators, AbstractControl } from '@angular/forms';
import { Router, ActivatedRoute, Params } from '@angular/router';
import { formatDate } from '@angular/common'
import { Account } from '../models/account';
import { LedgerService } from '../ledger.service';
import { Observable, switchMap } from 'rxjs';
import { isObject, omitBy } from "lodash-es"


function dateRange(group: FormGroup): {[key: string]: boolean} | null {
    const openedOn = group.get('opened_on')!.value;
    const closedOn = group.get('closed_on')!.value;

    if (!closedOn) {
        return null;
    }

    if (closedOn >= openedOn) {
        return null;
    }

    return { 'daterange': true }
}

@Component({
  selector: 'app-account-form',
  templateUrl: './account-form.component.html',
  styleUrls: ['./account-form.component.css']
})
export class AccountFormComponent implements OnInit {
    accountForm!: FormGroup;
    account: Account | undefined;
    errorMessage = '';
    datesExpanded = false;
    singularResourceName: string;

    constructor(
        private router: Router,
        private route: ActivatedRoute,
        private formBuilder: FormBuilder,
        private ledgerService: LedgerService
    ) {
        this.singularResourceName = 'account';
    }

    ngOnInit(): void {
        const id = Number(this.route.snapshot.paramMap.get('id') || 0)

        this.accountForm = this.formBuilder.group({
            name: [null, {updateOn: 'blur', validators: [Validators.required, Validators.minLength(3)]}],
            url: [null, {updatedOn: 'blur'}],
            dates: this.formBuilder.group({
                opened_on: this.today(),
                closed_on: null,
            }, {validators: dateRange}),
            note: ['', {updateOn: 'blur'}],
        });

        this.ledgerService.getAccount(id).subscribe(
            (account: Account) => this.populate(account),
            (err: any) => console.log(err),
            () => console.log('All done getting account'),
        );
    }

    ngOnDestroy(): void {
    }

    get name() { return this.accountForm.controls['name'] }
    get dates() { return this.accountForm.controls['dates'] as FormGroup }
    get openedOn() { return this.dates.controls['opened_on'] }
    get closedOn() { return this.dates.controls['closed_on'] }
    get note() { return this.accountForm.controls['note'] }
    get url() { return this.accountForm.get('url')!; }

    today() {
        return formatDate(new Date(), 'yyyy-MM-dd', 'en');
    }

    save(): void {
        const outboundAccount: Account = {
            ...this.account,
            ...omitBy(this.accountForm.value, (v, _) => {
                return isObject(v);
            }),
            ...this.dates.value,
        };

        if (outboundAccount.uid === 0) {
            console.log('yes');
            this.ledgerService.addAccount(outboundAccount).subscribe(
                () => this.saved(),
                (err) => this.errorMessage = err,
            );
        }

        if (outboundAccount.uid > 0) {
            this.ledgerService.updateAccount(outboundAccount).subscribe(
                () => this.saved(),
                (err) => this.errorMessage = err,
            );
        }
    }

    saved() {
        this.accountForm.reset();
        this.router.navigate(['/accounts']);
    }

    deleted() {
        this.accountForm.reset();
        this.router.navigate(['/accounts']);
    }

    canDelete(): boolean {
        if (!this.account) {
            return false;
        }
        return this.account.uid > 0;
    }

    reset() {
        if (this.account) {
            this.populate(this.account);
        }
   }

    populate(account: Account) {
        this.accountForm.reset();

        this.accountForm.patchValue({
            name: account.name,
            url: account.url,
            dates: {
                opened_on: account.opened_on,
                closed_on: account.closed_on,
            },
            note: account.note,
        });

        this.account = account;
        this.datesExpanded = (account.closed_on !== null);
    }

    toggleAccountClosed(event: Event) {
        this.datesExpanded = (event.target as HTMLInputElement).checked;
        this.accountForm.markAsDirty();

        this.dates.patchValue({
            closed_on: (this.datesExpanded)? this.today() : null,
        });
    }

    deleteAccount() {
        if (!this.account) {
            return;
        }

        this.ledgerService.deleteAccount(this.account.uid).subscribe(
            () => this.deleted(),
            (err) => this.errorMessage = err,
        );
    }
}
